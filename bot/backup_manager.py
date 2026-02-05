import asyncio
import json
import logging
import os
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from aiogram import Bot
from aiogram.types import FSInputFile
from zoneinfo import ZoneInfo

from bot import config

logger = logging.getLogger(__name__)


BACKUPS_DIR = Path("bot/backups")

# Храним только последние N бэкапов (старые удаляем автоматически)
MAX_BACKUPS_KEEP = 3


@dataclass
class BackupInfo:
    path: Path
    created_at: datetime


def _parse_backup_time(value: str) -> Tuple[int, int]:
    """Парсит BACKUP_TIME вида HH:MM."""
    try:
        hh, mm = value.strip().split(":")
        h = int(hh)
        m = int(mm)
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError
        return h, m
    except Exception:
        logger.warning("Invalid BACKUP_TIME='%s', fallback to 10:00", value)
        return 10, 0


def list_backups(limit: int = 10) -> List[BackupInfo]:
    """Возвращает список бэкапов (последние сверху)."""
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    items: List[BackupInfo] = []
    for p in BACKUPS_DIR.glob("aunt_polly_backup_*.zip"):
        try:
            ts = p.stem.replace("aunt_polly_backup_", "")
            created = datetime.strptime(ts, "%Y%m%d_%H%M%S").replace(tzinfo=timezone.utc)
        except Exception:
            created = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
        items.append(BackupInfo(path=p, created_at=created))
    items.sort(key=lambda x: x.created_at, reverse=True)
    return items[:limit]


def create_backup_file() -> Path:
    """Создаёт zip-бэкап настроек/FAQ и возвращает путь."""
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)

    now_utc = datetime.now(timezone.utc)
    filename = f"aunt_polly_backup_{now_utc.strftime('%Y%m%d_%H%M%S')}.zip"
    out_path = BACKUPS_DIR / filename

    # Дополнительно: если админ менял картинку приветствия — кладём её тоже в бэкап
    settings = config.load_json(config.SETTINGS_FILE, default_data={})
    welcome_image_path = (settings.get("welcome_image_path") or "").strip()
    extra_files: List[str] = []
    if welcome_image_path:
        p_img = Path(welcome_image_path)
        if p_img.exists() and p_img.is_file():
            extra_files.append(welcome_image_path)

    manifest = {
        "app": "aunt-polly-bot",
        "format": 1,
        "created_at_utc": now_utc.isoformat(),
        "includes": [config.SETTINGS_FILE, config.FAQ_FILE] + extra_files,
    }

    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        # Манифест
        z.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

        # Файлы данных
        for rel in (config.SETTINGS_FILE, config.FAQ_FILE):
            p = Path(rel)
            if p.exists():
                z.write(p, arcname=str(p))
            else:
                # Сохраним пустышку, чтобы восстановление было предсказуемым
                z.writestr(str(p), "{}" if rel.endswith("settings.json") else "[]")

        # Дополнительные файлы (например, изображение приветствия)
        for rel in extra_files:
            p = Path(rel)
            if p.exists() and p.is_file():
                z.write(p, arcname=str(p))

    # Авто-очистка старых бэкапов
    _cleanup_old_backups(MAX_BACKUPS_KEEP)

    logger.info("Backup created: %s", out_path)
    return out_path


def _cleanup_old_backups(max_keep: int) -> None:
    """Удаляет старые бэкапы, оставляя только последние max_keep."""
    try:
        backups = list_backups(limit=1000)
        if len(backups) <= max_keep:
            return
        to_delete = backups[max_keep:]
        for b in to_delete:
            try:
                b.path.unlink(missing_ok=True)
                logger.info("Deleted old backup: %s", b.path)
            except Exception:
                logger.warning("Could not delete old backup: %s", b.path, exc_info=True)
    except Exception:
        logger.warning("Backup cleanup failed", exc_info=True)


def restore_backup_file(zip_path: Path) -> str:
    """Восстанавливает настройки/FAQ из zip. Возвращает краткий отчёт."""
    if not zip_path.exists():
        raise FileNotFoundError(str(zip_path))

    restored = []
    with zipfile.ZipFile(zip_path, "r") as z:
        names = set(z.namelist())
        # Проверяем манифест (не обязателен, но желателен)
        manifest_includes: List[str] = []
        if "manifest.json" in names:
            try:
                manifest = json.loads(z.read("manifest.json").decode("utf-8"))
                manifest_includes = list(manifest.get("includes", []) or [])
                logger.info("Restoring backup manifest: %s", manifest)
            except Exception:
                logger.warning("Could not parse manifest.json in backup")

        # Базовые файлы
        base_targets = [config.SETTINGS_FILE, config.FAQ_FILE]
        for arc in base_targets:
            if arc not in names:
                continue
            target = Path(arc)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(z.read(arc))
            restored.append(arc)

        # Дополнительные файлы (например, картинка приветствия)
        for arc in manifest_includes:
            if arc in restored:
                continue
            if arc not in names:
                continue
            target = Path(arc)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(z.read(arc))
            restored.append(arc)

    if not restored:
        return "Нечего восстанавливать: в бэкапе нет settings/faq"
    return "Восстановлено: " + ", ".join(restored)


async def send_backup_to_admin(bot: Bot, backup_path: Path, caption: str) -> None:
    await bot.send_document(
        chat_id=config.ADMIN_ID,
        document=FSInputFile(str(backup_path)),
        caption=caption,
    )


async def run_daily_backup_loop(bot: Bot) -> None:
    """Фоновый цикл ежедневного бэкапа и отправки админу."""
    tz = ZoneInfo(config.TIMEZONE) if config.TIMEZONE else timezone.utc
    logger.info("Daily backup scheduler enabled (%s)", tz)

    while True:
        # Берём время из settings.json (можно менять из админ-панели без перезапуска)
        settings = config.load_json(config.SETTINGS_FILE, default_data={})
        bt = (settings.get("backup_time") or getattr(config, "BACKUP_TIME", "10:00")).strip()
        hour, minute = _parse_backup_time(bt)

        now = datetime.now(tz)
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_run <= now:
            next_run = next_run + timedelta(days=1)

        sleep_s = (next_run - now).total_seconds()
        logger.info("Next daily backup at %s (in %.0f sec)", next_run.isoformat(), sleep_s)
        await asyncio.sleep(max(1, sleep_s))

        try:
            p = create_backup_file()
            # Отправляем админу
            local_time = datetime.now(tz).strftime("%d.%m.%Y %H:%M")
            await send_backup_to_admin(
                bot,
                p,
                caption=f"🗄️ Ежедневный бэкап настроек • {local_time}\n\nФайл содержит FAQ и настройки админ-панели.",
            )
        except Exception as e:
            logger.error("Daily backup failed: %s", e, exc_info=True)
