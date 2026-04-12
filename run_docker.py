import os
from subprocess import run

from dotenv import load_dotenv


load_dotenv()

BOT_TOKEN = "BOT_TOKEN"
ADMIN_IDS = "ADMIN_IDS"
YUQA_DATA_DIR = "YUQA_DATA_DIR"
YUQA_AUTO_MIGRATE = "YUQA_AUTO_MIGRATE"
DATABASE_URL = "DATABASE_URL"

res = run([
    "docker", "run", "-d", "--restart", "unless-stopped", "--name", "app",
    "-p", "80:8000",
    "-e", f"{BOT_TOKEN}={os.getenv(BOT_TOKEN)}",
    "-e", f"{ADMIN_IDS}={os.getenv(ADMIN_IDS)}",
    "-e", f"{YUQA_AUTO_MIGRATE}={os.getenv(YUQA_AUTO_MIGRATE)}",
    "-e", f"{DATABASE_URL}={os.getenv(DATABASE_URL)}",
    "registry.gitlab.com/loh228putin-group/yuqa:latest",
], capture_output=True)

if not res.stderr:
    exit(0)

