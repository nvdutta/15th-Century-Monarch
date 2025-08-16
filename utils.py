import os
import logging
import logging.handlers
from datetime import datetime
import pytz

def today() -> str:
    """Returns today's date in YYYY-MM-DD format."""
    return datetime.now(pytz.timezone("US/Eastern")).strftime("%Y-%m-%d")

def old_times_today() -> str:
    """Returns today's date in the year 1462 in YYYY-MM-DD format."""
    old_date = "1462-"
    old_date += datetime.now(pytz.timezone("US/Eastern")).strftime("%m-%d")
    return old_date

def setup_logging(config: dict) -> logging.Logger:
    """Setup logging configuration."""
    logging_config = config['logging']
    
    # Create logs directory if it doesn't exist
    if not os.path.exists(logging_config['directory']):
        os.makedirs(logging_config['directory'])
    
    logger = logging.getLogger('discord')
    formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
    
    log_path = os.path.join(logging_config['directory'], logging_config['file_name'])
    handler = logging.handlers.TimedRotatingFileHandler(
        log_path, 
        when=logging_config['rotation'], 
        backupCount=logging_config['backup_count']
    )
    handler.namer = lambda name: name + ".log"
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger