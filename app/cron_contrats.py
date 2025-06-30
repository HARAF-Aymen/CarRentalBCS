import mysql.connector
from datetime import date
import time

def update_expired_contracts():
    try:
        conn = mysql.connector.connect(
            host="localhost",         # ou ton IP MySQL
            user="root",
            password="1234",
            database="locvoiture_db"
        )
        cursor = conn.cursor()

        update_query = """
        UPDATE contrats_location
        SET statut = 'TERMINE'
        WHERE date_fin < %s AND statut != 'TERMINE'
        """
        cursor.execute(update_query, (date.today(),))
        conn.commit()

        print(f"[{date.today()}] {cursor.rowcount} contrat(s) mis à jour avec statut = 'TERMINE'.")

        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        print(f"❌ Erreur MySQL : {err}")

if __name__ == "__main__":
    print("⏳ Démarrage du job de surveillance des contrats expirés...")
    while True:
        update_expired_contracts()
        time.sleep(60)  # ⏱ toutes les 60 secondes
