from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import os
import random
from datetime import datetime, timedelta

# Dossier de sortie
output_dir = "factures"
os.makedirs(output_dir, exist_ok=True)

def generate_invoice_pdf(invoice_number, client_name, date, amount, filename):
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 50, f"Facture n° :  #{invoice_number}")

    c.setFont("Helvetica", 12)
    c.drawString(50, height - 100, f"Date: {date.strftime('%d/%m/%Y')}")
    c.drawString(50, height - 120, f"Client: {client_name}")
    c.drawString(50, height - 140, f"Montant Total : {amount:.2f} €")

    # Tableau exemple
    c.drawString(50, height - 180, "Description")
    c.drawString(300, height - 180, "Quantité")
    c.drawString(400, height - 180, "Prix")

    for i in range(3):
        y = height - 200 - i*20
        c.drawString(50, y, f"Produit {i+1}")
        qty = random.randint(1, 5)
        price = random.uniform(10, 100)
        c.drawString(300, y, str(qty))
        c.drawString(400, y, f"{price:.2f} €")

    c.showPage()
    c.save()

# Liste de clients
clients = ["Jerom Dupont", "Hneri Martin", "Maxime Durand", "Laurent Lefevre", "Jordan Moreau", 
           "Arthur Girard", "Jérémy Bernard", "Maurice Petit", "Axel Roux", "Juste Leblanc"]

# Générer plusieurs factures par client
invoice_number = 1000
for client_name in clients:
    nb_factures = random.randint(3, 7)  # chaque client a entre 3 et 7 factures
    for _ in range(nb_factures):
        date = datetime.now() - timedelta(days=random.randint(0, 60))
        amount = random.uniform(50, 500)
        filename = os.path.join(output_dir, f"facture_{client_name}_{invoice_number}.pdf")
        generate_invoice_pdf(invoice_number, client_name, date, amount, filename)
        invoice_number += 1

print(f"✅ Factures PDF générées dans le dossier '{output_dir}'")

if __name__ == "__main__":
    generate_invoice_pdf(2001, "Client Test", datetime.now(), random.uniform(50, 500), "facture_test.pdf")