from core import db_manager

def main():
    db_manager.init_db()
    print("Banco inicializado/migrado com sucesso.")

if __name__ == "__main__":
    main()
