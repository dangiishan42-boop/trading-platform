from app.config.settings import get_settings

settings = get_settings()

BASE_DIR = settings.base_dir
DATA_DIR = settings.data_path
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
SAMPLE_DATA_DIR = DATA_DIR / "samples"
LOG_DIR = BASE_DIR / "logs"
