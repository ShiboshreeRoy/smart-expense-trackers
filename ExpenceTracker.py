import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk
import sqlite3
import pytesseract
import cv2
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import speech_recognition as sr
import datetime
import os

# Database Setup
conn = sqlite3.connect("expenses.db")
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS expenses (
             id INTEGER PRIMARY KEY,
             date TEXT,
             category TEXT,
             description TEXT,
             amount REAL
             )''')
conn.commit()

# Main App
class ExpenseTracker:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart Expense Tracker")
        self.root.geometry("1400x800")  # Increased window size
        self.setup_ui()

    def setup_ui(self):
        ctk.set_appearance_mode("dark")  # Default to dark mode
        ctk.set_default_color_theme("dark-blue")

        self.tab_control = ttk.Notebook(self.root)

        self.dashboard_tab = ctk.CTkFrame(self.tab_control)
        self.add_tab = ctk.CTkFrame(self.tab_control)
        self.scan_tab = ctk.CTkFrame(self.tab_control)
        self.history_tab = ctk.CTkFrame(self.tab_control)
        self.about_tab = ctk.CTkFrame(self.tab_control)

        self.tab_control.add(self.dashboard_tab, text='Dashboard')
        self.tab_control.add(self.add_tab, text='Add Expense')
        self.tab_control.add(self.scan_tab, text='Scan Receipt')
        self.tab_control.add(self.history_tab, text='Expense History')
        self.tab_control.add(self.about_tab, text='About')

        self.tab_control.pack(expand=1, fill='both')

        self.setup_dashboard()
        self.setup_add_tab()
        self.setup_scan_tab()
        self.setup_history_tab()
        self.setup_about_tab()

        self.mode_toggle = ctk.CTkSwitch(self.root, text="Toggle Dark/Light Mode", command=self.toggle_mode, font=("Arial", 16))
        self.mode_toggle.pack(pady=20)

    def toggle_mode(self):
        current_mode = ctk.get_appearance_mode()
        ctk.set_appearance_mode("light" if current_mode == "dark" else "dark")

    def setup_dashboard(self):
        self.refresh_button = ctk.CTkButton(self.dashboard_tab, text="Refresh", command=self.plot_expenses, font=("Arial", 16))
        self.refresh_button.pack(pady=20)

        self.figure = plt.Figure(figsize=(6, 5), dpi=100)
        self.chart = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, self.dashboard_tab)
        self.canvas.get_tk_widget().pack()
        self.plot_expenses()

    def plot_expenses(self):
        self.chart.clear()
        c.execute("SELECT category, SUM(amount) FROM expenses GROUP BY category")
        data = c.fetchall()
        categories = [row[0] for row in data]
        amounts = [row[1] for row in data]
        self.chart.pie(amounts, labels=categories, autopct='%1.1f%%')
        self.chart.set_title('Expenses by Category', fontsize=18)
        self.canvas.draw()

    def setup_add_tab(self):
        self.date_label = ctk.CTkLabel(self.add_tab, text="Date (YYYY-MM-DD)", font=("Arial", 16))
        self.date_label.pack(pady=10)
        self.date_entry = ctk.CTkEntry(self.add_tab, font=("Arial", 16))
        self.date_entry.insert(0, datetime.date.today().isoformat())
        self.date_entry.pack(pady=10)

        self.category_label = ctk.CTkLabel(self.add_tab, text="Category", font=("Arial", 16))
        self.category_label.pack(pady=10)
        self.category_entry = ctk.CTkEntry(self.add_tab, font=("Arial", 16))
        self.category_entry.pack(pady=10)

        self.desc_label = ctk.CTkLabel(self.add_tab, text="Description", font=("Arial", 16))
        self.desc_label.pack(pady=10)
        self.desc_entry = ctk.CTkEntry(self.add_tab, font=("Arial", 16))
        self.desc_entry.pack(pady=10)

        self.amount_label = ctk.CTkLabel(self.add_tab, text="Amount", font=("Arial", 16))
        self.amount_label.pack(pady=10)
        self.amount_entry = ctk.CTkEntry(self.add_tab, font=("Arial", 16))
        self.amount_entry.pack(pady=10)

        self.add_btn = ctk.CTkButton(self.add_tab, text="Add Expense", command=self.add_expense, font=("Arial", 16))
        self.add_btn.pack(pady=20)

        self.voice_btn = ctk.CTkButton(self.add_tab, text="Add by Voice 🎙️", command=self.voice_input, font=("Arial", 16))
        self.voice_btn.pack(pady=20)

    def add_expense(self):
        date = self.date_entry.get()
        cat = self.category_entry.get()
        desc = self.desc_entry.get()
        amount = self.amount_entry.get()

        if not amount.replace('.', '', 1).isdigit():
            messagebox.showerror("Input Error", "Amount must be a number.")
            return

        try:
            c.execute("INSERT INTO expenses (date, category, description, amount) VALUES (?, ?, ?, ?)",
                      (date, cat, desc, float(amount)))
            conn.commit()
            messagebox.showinfo("Success", "Expense added!")
            self.refresh_expense_history()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def voice_input(self):
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            messagebox.showinfo("Voice Input", "Speak something like 'Add 100 groceries'...")
            audio = recognizer.listen(source)
        try:
            text = recognizer.recognize_google(audio)
            print("You said:", text)
            words = text.split()
            amount = float([word for word in words if word.replace('.', '', 1).isdigit()][0])
            cat = next(word for word in words if not word.replace('.', '', 1).isdigit())
            self.category_entry.delete(0, tk.END)
            self.category_entry.insert(0, cat)
            self.amount_entry.delete(0, tk.END)
            self.amount_entry.insert(0, str(amount))
        except Exception as e:
            messagebox.showerror("Error", f"Could not understand. {str(e)}")

    def setup_scan_tab(self):
        self.upload_btn = ctk.CTkButton(self.scan_tab, text="Upload Receipt", command=self.upload_receipt, font=("Arial", 16))
        self.upload_btn.pack(pady=20)

        self.receipt_text = ctk.CTkTextbox(self.scan_tab, height=20, font=("Arial", 16))
        self.receipt_text.pack(fill='both', expand=True)

    def upload_receipt(self):
        file_path = filedialog.askopenfilename()
        if not file_path:
            return
        try:
            image = cv2.imread(file_path)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            text = pytesseract.image_to_string(gray)
            self.receipt_text.delete(1.0, tk.END)
            self.receipt_text.insert(tk.END, text)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def setup_history_tab(self):
        self.history_label = ctk.CTkLabel(self.history_tab, text="Expense History", font=("Arial", 18))
        self.history_label.pack(pady=20)

        self.search_entry = ctk.CTkEntry(self.history_tab, placeholder_text="Search by Category or Amount", font=("Arial", 16))
        self.search_entry.pack(pady=10)

        self.search_btn = ctk.CTkButton(self.history_tab, text="Search", command=self.search_expenses, font=("Arial", 16))
        self.search_btn.pack(pady=20)

        self.expense_tree = ttk.Treeview(self.history_tab, columns=("ID", "Date", "Category", "Description", "Amount"), show="headings")
        self.expense_tree.heading("ID", text="ID")
        self.expense_tree.heading("Date", text="Date")
        self.expense_tree.heading("Category", text="Category")
        self.expense_tree.heading("Description", text="Description")
        self.expense_tree.heading("Amount", text="Amount")
        self.expense_tree.pack(fill="both", expand=True)

        self.refresh_expense_history()

        self.edit_btn = ctk.CTkButton(self.history_tab, text="Edit Expense", command=self.edit_expense, font=("Arial", 16))
        self.edit_btn.pack(pady=20)

        self.delete_btn = ctk.CTkButton(self.history_tab, text="Delete Expense", command=self.delete_expense, font=("Arial", 16))
        self.delete_btn.pack(pady=20)

    def search_expenses(self):
        query = self.search_entry.get()
        if not query:
            self.refresh_expense_history()
            return

        c.execute("SELECT * FROM expenses WHERE category LIKE ? OR description LIKE ? OR amount LIKE ?",
                  ('%' + query + '%', '%' + query + '%', '%' + query + '%'))
        data = c.fetchall()

        for item in self.expense_tree.get_children():
            self.expense_tree.delete(item)

        for row in data:
            self.expense_tree.insert("", "end", values=row)

    def refresh_expense_history(self):
        c.execute("SELECT * FROM expenses")
        data = c.fetchall()

        for item in self.expense_tree.get_children():
            self.expense_tree.delete(item)

        for row in data:
            self.expense_tree.insert("", "end", values=row)

    def edit_expense(self):
        selected_item = self.expense_tree.selection()
        if not selected_item:
            messagebox.showerror("Selection Error", "Please select an expense to edit.")
            return

        item = self.expense_tree.item(selected_item)
        expense_id = item['values'][0]
        date = item['values'][1]
        category = item['values'][2]
        description = item['values'][3]
        amount = item['values'][4]

        edit_window = ctk.CTkToplevel(self.root)
        edit_window.title("Edit Expense")
        edit_window.geometry("400x300")

        ctk.CTkLabel(edit_window, text="Date (YYYY-MM-DD)", font=("Arial", 16)).pack(pady=10)
        edit_date_entry = ctk.CTkEntry(edit_window, font=("Arial", 16))
        edit_date_entry.insert(0, date)
        edit_date_entry.pack(pady=10)

        ctk.CTkLabel(edit_window, text="Category", font=("Arial", 16)).pack(pady=10)
        edit_category_entry = ctk.CTkEntry(edit_window, font=("Arial", 16))
        edit_category_entry.insert(0, category)
        edit_category_entry.pack(pady=10)

        ctk.CTkLabel(edit_window, text="Description", font=("Arial", 16)).pack(pady=10)
        edit_desc_entry = ctk.CTkEntry(edit_window, font=("Arial", 16))
        edit_desc_entry.insert(0, description)
        edit_desc_entry.pack(pady=10)

        ctk.CTkLabel(edit_window, text="Amount", font=("Arial", 16)).pack(pady=10)
        edit_amount_entry = ctk.CTkEntry(edit_window, font=("Arial", 16))
        edit_amount_entry.insert(0, amount)
        edit_amount_entry.pack(pady=10)

        def save_changes():
            new_date = edit_date_entry.get()
            new_category = edit_category_entry.get()
            new_description = edit_desc_entry.get()
            new_amount = edit_amount_entry.get()

            if not new_amount.replace('.', '', 1).isdigit():
                messagebox.showerror("Input Error", "Amount must be a number.")
                return

            c.execute("UPDATE expenses SET date = ?, category = ?, description = ?, amount = ? WHERE id = ?",
                      (new_date, new_category, new_description, float(new_amount), expense_id))
            conn.commit()
            edit_window.destroy()
            messagebox.showinfo("Success", "Expense updated!")
            self.refresh_expense_history()

        ctk.CTkButton(edit_window, text="Save Changes", command=save_changes, font=("Arial", 16)).pack(pady=20)

    def delete_expense(self):
        selected_item = self.expense_tree.selection()
        if not selected_item:
            messagebox.showerror("Selection Error", "Please select an expense to delete.")
            return

        item = self.expense_tree.item(selected_item)
        expense_id = item['values'][0]

        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete the expense ID {expense_id}?")
        if confirm:
            c.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
            conn.commit()
            messagebox.showinfo("Success", "Expense deleted!")
            self.refresh_expense_history()

    def setup_about_tab(self):
        title = ctk.CTkLabel(self.about_tab, text="Smart Expense Tracker", font=("Arial", 24, "bold"))
        title.pack(pady=20)

        dev = ctk.CTkLabel(self.about_tab, text="Developer: Shiboshree Roy", font=("Arial", 18))
        dev.pack(pady=10)

        version = ctk.CTkLabel(self.about_tab, text="Version: 1.0", font=("Arial", 18))
        version.pack(pady=10)

        email = ctk.CTkLabel(self.about_tab, text="Contact: shiboshreeroy169@gmail.com", font=("Arial", 18))
        email.pack(pady=10)


if __name__ == "__main__":
    root = tk.Tk()
    app = ExpenseTracker(root)
    root.mainloop()
