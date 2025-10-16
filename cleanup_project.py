import os
import shutil
from datetime import datetime
import logging

# Configurações
PROJECT_DIR = "C:/Users/Pichau/Desktop/v1.0.13"  # Diretório do projeto atualizado
SCRIPTS_DIR = os.path.join(PROJECT_DIR, "scripts")  # Pasta destino
LOG_FILE = "cleanup_log.txt"  # Arquivo de log
BACKUP_DIR = os.path.join(PROJECT_DIR, "backup_" + datetime.now().strftime("%Y%m%d_%H%M%S"))  # Pasta de backup

# Lista de arquivos a verificar e mover (do relatório)
FILES_TO_CHECK = [
    "config/__init__.py",
    "config/logging_config.py",
    "config/settings.py",
    "detectors/__init__.py",
    "infra/__init__.py",
    "infra/db/__init__.py",
    "infra/db/init_db.py",
    "infra/upload_queue.py",
    "scripts/healthcheck.py",
    "scripts/smoke_test.py",
    "ui/__init__.py",
    "ui/dialogs.py",
    "ui/menu/__init__.py",
    "ui/subpastas/__init__.py",
    "ui/users/__init__.py",
    "ui/users/users.py"
]

def setup_logging():
    """Configura o logging para registrar ações."""
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

def is_file_empty_or_comments(file_path):
    """Verifica se o arquivo está vazio ou contém apenas comentários."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in lines:
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    return False
        return True
    except Exception as e:
        logging.error(f"Erro ao verificar {file_path}: {e}")
        return False

def create_backup():
    """Cria um backup da pasta do projeto."""
    if os.path.exists(PROJECT_DIR):
        logging.info(f"Criando backup em {BACKUP_DIR}")
        shutil.copytree(PROJECT_DIR, BACKUP_DIR, dirs_exist_ok=True)
        print(f"Backup criado em {BACKUP_DIR}")
    else:
        logging.error("Diretório do projeto não encontrado!")
        print("Erro: Diretório do projeto não encontrado!")

def ensure_scripts_dir():
    """Garante que a pasta scripts/ existe."""
    if not os.path.exists(SCRIPTS_DIR):
        os.makedirs(SCRIPTS_DIR)
        logging.info(f"Pasta {SCRIPTS_DIR} criada")
        print(f"Pasta {SCRIPTS_DIR} criada")

def move_file(file_path):
    """Move o arquivo para a pasta scripts/."""
    file_name = os.path.basename(file_path)
    dest_path = os.path.join(SCRIPTS_DIR, file_name)
    try:
        shutil.move(file_path, dest_path)
        logging.info(f"Arquivo {file_path} movido para {dest_path}")
        print(f"Arquivo {file_path} movido para {dest_path}")
    except Exception as e:
        logging.error(f"Erro ao mover {file_path}: {e}")
        print(f"Erro ao mover {file_path}: {e}")

def main():
    """Função principal para verificar e mover arquivos."""
    setup_logging()
    print("Iniciando limpeza do projeto...")
    logging.info("Iniciando limpeza do projeto")

    # Criar backup
    create_backup()

    # Garantir que scripts/ existe
    ensure_scripts_dir()

    # Verificar e mover arquivos
    for file in FILES_TO_CHECK:
        file_path = os.path.join(PROJECT_DIR, file)
        if os.path.exists(file_path):
            if is_file_empty_or_comments(file_path):
                logging.info(f"Arquivo {file_path} está vazio ou só tem comentários")
                print(f"Arquivo {file_path} está vazio ou só tem comentários")
            else:
                logging.info(f"Arquivo {file_path} contém código; verifique manualmente")
                print(f"Arquivo {file_path} contém código; verifique manualmente")
            move_file(file_path)
        else:
            logging.warning(f"Arquivo {file_path} não encontrado")
            print(f"Arquivo {file_path} não encontrado")

    print("Limpeza concluída! Verifique o log em", LOG_FILE)
    logging.info("Limpeza concluída")

if __name__ == "__main__":
    main()