import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime

from model import DataStore, BikeType, LocationType, Role, BikeStatus


class BikerApp(tk.Tk):
    """
    Eenvoudige Tkinter GUI met login per rol.
    - Login-scherm (rol + gebruikersnaam + wachtwoord)
    - Huurder: eigen reserveringen + nieuwe reservering + 'Mijn gegevens' + uitloggen
    - Beheerder: tabbladen Bestellingen en Fietsen + uitloggen
    - Monteur: overzicht reparaties + fiets herstellen + uitloggen
    """

    def __init__(self):
        super().__init__()

        self.title("BIKER Light")
        self.geometry("900x650")

        self.store = DataStore()
        self.store.load_from_csv(".")   # data laden uit CSV


        self.current_account = None
        self.current_role: Role | None = None

        # login-scherm
        self.login_frame = ttk.Frame(self)
        self.build_login_frame()
        self.login_frame.pack(fill="both", expand=True)

        # hoofd-UI (na inloggen)
        self.main_frame = None
        self.notebook = None

        self.protocol("WM_DELETE_WINDOW", self.on_close)


    # ---------- login-UI ----------

    def build_login_frame(self):
        frame = self.login_frame

        title = ttk.Label(frame, text="Inloggen bij BIKER", font=("Arial", 14, "bold"))
        title.pack(pady=15)

        form = ttk.Frame(frame)
        form.pack(pady=10)

        ttk.Label(form, text="Rol:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.role_var = tk.StringVar()
        self.role_combo = ttk.Combobox(
            form,
            textvariable=self.role_var,
            values=[r.value for r in Role],
            state="readonly",
            width=20,
        )
        self.role_combo.grid(row=0, column=1, padx=5, pady=5)
        self.role_combo.current(0)

        ttk.Label(form, text="Gebruikersnaam:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.username_entry = ttk.Entry(form, width=22)
        self.username_entry.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(form, text="Wachtwoord:").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.password_entry = ttk.Entry(form, show="*", width=22)
        self.password_entry.grid(row=2, column=1, padx=5, pady=5)

        btn_login = ttk.Button(form, text="Inloggen", command=self.handle_login)
        btn_login.grid(row=3, column=0, columnspan=2, pady=10)

        hint = ttk.Label(
            frame,
            text="Demo-accounts:\n"
                 
                 "Klant Dima:  dima / test\n"
                 "Klant Anna:  anna / test\n"
                 "Klant Darian:  darian / test\n"
                 "Beheerder: admin / admin\n"
                 "Monteur:  monteur / monteur",
            foreground="gray",
        )
        hint.pack(pady=5)

    def handle_login(self):
        role_text = self.role_var.get()
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        if not username or not password:
            messagebox.showwarning("Ontbrekende gegevens", "Vul gebruikersnaam en wachtwoord in.")
            return

        role = Role(role_text)
        acc = self.store.authenticate(username, password, role)
        if acc is None:
            messagebox.showerror("Inloggen mislukt", "Onjuiste combinatie van rol / gebruikersnaam / wachtwoord.")
            return

        if role == Role.HUURDER and acc.customer_id is None:
            messagebox.showerror("Fout", "Deze huurder heeft geen gekoppelde klant.")
            return

        self.current_account = acc
        self.current_role = role

        self.login_frame.pack_forget()
        self.build_main_ui()

    # ---------- hoofd-UI ----------

    def build_main_ui(self):
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill="both", expand=True)

        top = ttk.Frame(self.main_frame)
        top.pack(fill="x", padx=10, pady=5)

        ttk.Label(
            top,
            text=f"Ingelogd als: {self.current_account.username} ({self.current_role.value})",
            font=("Arial", 12, "bold")
        ).pack(side="left")

        ttk.Button(top, text="Uitloggen", command=self.logout).pack(side="right")

        if self.current_role == Role.HUURDER:
            self.build_huurder_screen()
        elif self.current_role == Role.BEHEERDER:
            self.build_beheerder_screen()
        elif self.current_role == Role.MONTEUR:
            self.build_monteur_screen()

    def clear_main_content(self):
        if self.main_frame is not None:
            self.main_frame.destroy()
            self.main_frame = None
            self.notebook = None

    def logout(self):
        """Terug naar het login-scherm."""
        self.current_account = None
        self.current_role = None
        self.clear_main_content()
        self.login_frame.pack(fill="both", expand=True)

    # ========== Huurder-scherm ==========

    def build_huurder_screen(self):
        frame = ttk.Frame(self.main_frame)
        frame.pack(fill="both", expand=True, padx=10, pady=5)


        # klantselectie (voor huurder vast gekoppeld aan account)
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill="x", pady=0)

        # knop 'Mijn gegevens'
        ttk.Button(button_frame, text="Mijn gegevens", command=self.open_mijn_gegevens) \
            .pack(side="left")

        self.customer_var = tk.StringVar()


        ttk.Button(button_frame, text="Ververs", command=self.show_customer_reservations)\
            .pack(side="left", padx=5)

        # tabel met reserveringen
        res_frame = ttk.LabelFrame(frame, text="Mijn reserveringen")
        res_frame.pack(fill="both", expand=True, pady=5)

        self.res_tree = ttk.Treeview(
            res_frame,
            columns=("id", "bike", "start", "end", "locatie", "prijs"),
            show="headings",
        )
        for col, text in zip(
            ("id", "bike", "start", "end", "locatie", "prijs"),
            ("#", "Fiets", "Start", "Einde", "Locatie", "Prijs (€)")
        ):
            self.res_tree.heading(col, text=text)
            self.res_tree.column(col, width=110)
        self.res_tree.pack(side="left", fill="both", expand=True)

        scroll = ttk.Scrollbar(res_frame, orient="vertical", command=self.res_tree.yview)
        self.res_tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")

        # formulier nieuwe reservering
        form = ttk.LabelFrame(frame, text="Nieuwe reservering")
        form.pack(fill="x", pady=5)

        ttk.Label(form, text="Type fiets:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.bike_type_var = tk.StringVar()
        self.bike_type_combo = ttk.Combobox(
            form,
            textvariable=self.bike_type_var,
            values=[b.value for b in BikeType],
            state="readonly",
            width=15,
        )
        self.bike_type_combo.grid(row=0, column=1, padx=5, pady=2)
        self.bike_type_combo.current(0)

        ttk.Label(form, text="Start (YYYY-MM-DD HH:MM):").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.start_entry = ttk.Entry(form, width=20)
        self.start_entry.grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(form, text="Einde (YYYY-MM-DD HH:MM):").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.end_entry = ttk.Entry(form, width=20)
        self.end_entry.grid(row=2, column=1, padx=5, pady=2)

        ttk.Label(form, text="Locatie:").grid(row=0, column=2, padx=5, pady=2, sticky="w")
        self.location_var = tk.StringVar(value=LocationType.OPHALEN.value)
        ttk.Radiobutton(form, text="Ophalen", variable=self.location_var,
                        value=LocationType.OPHALEN.value).grid(row=0, column=3, sticky="w")
        ttk.Radiobutton(form, text="Bezorgen", variable=self.location_var,
                        value=LocationType.BEZORGEN.value).grid(row=1, column=3, sticky="w")

        ttk.Label(form, text="Afleveradres (bij bezorgen):").grid(row=2, column=2, padx=5, pady=2, sticky="w")
        self.address_entry = ttk.Entry(form, width=30)
        self.address_entry.grid(row=2, column=3, padx=5, pady=2)

        ttk.Button(form, text="Nieuwe reservering", command=self.create_reservation)\
            .grid(row=3, column=0, columnspan=4, pady=5)

        # defect melden
        defect = ttk.LabelFrame(frame, text="Defect melden")
        defect.pack(fill="x", pady=5)

        ttk.Label(defect, text="Reserveringsnummer:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.def_res_entry = ttk.Entry(defect, width=10)
        self.def_res_entry.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(defect, text="Defecttype:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.def_type_entry = ttk.Entry(defect, width=20)
        self.def_type_entry.grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(defect, text="Omschrijving:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.def_desc_entry = ttk.Entry(defect, width=40)
        self.def_desc_entry.grid(row=2, column=1, columnspan=3, padx=5, pady=2, sticky="w")

        ttk.Button(defect, text="Melding versturen", command=self.send_defect)\
            .grid(row=3, column=0, columnspan=4, pady=5)

        self.after(100, self.show_customer_reservations)

    # --- helpers huurder / algemeen ---

    def refresh_customer_combo(self):
        values = [f"{c.customer_id} – {c.name}" for c in self.store.customers.values()]
        self.customer_combo["values"] = values
        if values and not self.customer_var.get():
            self.customer_combo.current(0)

    def get_selected_customer_id(self):
        if self.current_role == Role.HUURDER and self.current_account.customer_id is not None:
            return self.current_account.customer_id

        value = self.customer_var.get()
        if not value:
            return None
        try:
            return int(value.split("–")[0].strip())
        except Exception:
            return None

    def show_customer_reservations(self):
        customer_id = self.get_selected_customer_id()
        if customer_id is None:
            messagebox.showwarning("Geen klant", "Selecteer eerst een klant.")
            return
        reservations = self.store.get_reservations_for_customer(customer_id)

        for row in self.res_tree.get_children():
            self.res_tree.delete(row)

        for r in reservations:
            self.res_tree.insert(
                "",
                "end",
                values=(
                    r.reservation_id,
                    r.bike_type.value,
                    r.start.strftime("%Y-%m-%d %H:%M"),
                    r.end.strftime("%Y-%m-%d %H:%M"),
                    r.location_type.value,
                    f"{r.total_price:.2f}",
                ),
            )

    def create_reservation(self):
        customer_id = self.get_selected_customer_id()
        if customer_id is None:
            messagebox.showwarning("Geen klant", "Selecteer eerst een klant.")
            return

        bike_text = self.bike_type_var.get()
        try:
            bike_type = BikeType(bike_text)
        except ValueError:
            messagebox.showerror("Fout", "Ongeldig fietstype.")
            return

        start_text = self.start_entry.get().strip()
        end_text = self.end_entry.get().strip()

        try:
            start_dt = datetime.strptime(start_text, "%Y-%m-%d %H:%M")
            end_dt = datetime.strptime(end_text, "%Y-%m-%d %H:%M")
        except ValueError:
            messagebox.showerror("Fout", "Gebruik formaat: YYYY-MM-DD HH:MM.")
            return

        loc_text = self.location_var.get()
        location = LocationType(loc_text)
        address = self.address_entry.get().strip() if location == LocationType.BEZORGEN else ""

        try:
            res = self.store.create_reservation(
                customer_id=customer_id,
                bike_type=bike_type,
                start=start_dt,
                end=end_dt,
                location_type=location,
                address=address,
            )
        except ValueError as e:
            messagebox.showerror("Fout", str(e))
            return

        messagebox.showinfo(
            "Reservering gemaakt",
            f"Reservering #{res.reservation_id} aangemaakt.\nTotaalprijs: € {res.total_price:.2f}",
        )
        self.show_customer_reservations()

    def send_defect(self):
        res_id_text = self.def_res_entry.get().strip()
        if not res_id_text.isdigit():
            messagebox.showerror("Fout", "Voer een geldig reserveringsnummer in.")
            return
        res_id = int(res_id_text)

        defect_type = self.def_type_entry.get().strip()
        description = self.def_desc_entry.get().strip()

        if not defect_type or not description:
            messagebox.showwarning("Ontbrekende gegevens", "Vul defecttype en omschrijving in.")
            return

        try:
            repair = self.store.report_defect(reservation_id=res_id, defect_type=defect_type, description=description)
        except ValueError as e:
            messagebox.showerror("Fout", str(e))
            return

        messagebox.showinfo(
            "Defect gemeld",
            f"Reparatie #{repair.repair_id} aangemaakt voor fiets {repair.bike_id}.",
        )
        self.def_res_entry.delete(0, "end")
        self.def_type_entry.delete(0, "end")
        self.def_desc_entry.delete(0, "end")

    def open_mijn_gegevens(self):
        """Open een apart venster waarin de huurder zijn gegevens kan bijwerken."""
        customer_id = self.get_selected_customer_id()
        if customer_id is None or customer_id not in self.store.customers:
            messagebox.showwarning("Geen klant", "Geen gekoppelde klant gevonden.")
            return
        cust = self.store.customers[customer_id]

        win = tk.Toplevel(self)
        win.title("Mijn gegevens")
        win.geometry("400x250")

        ttk.Label(win, text="Naam:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        name_var = tk.StringVar(value=cust.name)
        name_entry = ttk.Entry(win, textvariable=name_var, width=30)
        name_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(win, text="E-mail:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        email_var = tk.StringVar(value=cust.email)
        email_entry = ttk.Entry(win, textvariable=email_var, width=30)
        email_entry.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(win, text="IBAN (optioneel):").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        iban_var = tk.StringVar(value=cust.iban)
        iban_entry = ttk.Entry(win, textvariable=iban_var, width=30)
        iban_entry.grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(win, text="Afleveradres (optioneel):").grid(row=3, column=0, padx=5, pady=5, sticky="e")
        addr_var = tk.StringVar(value=cust.delivery_address)
        addr_entry = ttk.Entry(win, textvariable=addr_var, width=30)
        addr_entry.grid(row=3, column=1, padx=5, pady=5)

        def opslaan():
            cust.name = name_var.get().strip()
            cust.email = email_var.get().strip()
            cust.iban = iban_var.get().strip()
            cust.delivery_address = addr_var.get().strip()
            self.refresh_customer_combo()

            # meteen naar csv schrijven (dezelfde map)
            self.store.save_to_csv(".")

            messagebox.showinfo("Opgeslagen", "Je gegevens zijn bijgewerkt.")
            win.destroy()

        ttk.Button(win, text="Opslaan", command=opslaan).grid(row=4, column=0, columnspan=2, pady=10)

    # ========== Beheerder-scherm ==========

    def build_beheerder_screen(self):
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.build_beheerder_bestellingen_tab()
        self.build_beheerder_fietsen_tab()

    def build_beheerder_bestellingen_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Reserveringen")

        # tabel met alle reserveringen
        frame = ttk.LabelFrame(tab, text="Alle reserveringen")
        frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.admin_tree = ttk.Treeview(
            frame,
            columns=("id", "klant", "bike", "start", "end", "locatie", "prijs"),
            show="headings",
        )
        headers = ["#", "Klant", "Fiets", "Start", "Einde", "Locatie", "Prijs (€)"]
        for col, text in zip(("id", "klant", "bike", "start", "end", "locatie", "prijs"), headers):
            self.admin_tree.heading(col, text=text)
            self.admin_tree.column(col, width=110)
        self.admin_tree.pack(side="left", fill="both", expand=True)

        scroll = ttk.Scrollbar(frame, orient="vertical", command=self.admin_tree.yview)
        self.admin_tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")

        # frame voor de knoppen
        button_frame = ttk.Frame(tab)
        button_frame.pack(fill='x', pady=5)

        # knop om geselecteerde reservering te bewerken
        ttk.Button(button_frame, text="Bewerk geselecteerde reservering",
                   command=self.edit_selected_reservation).pack(side="left", padx=5)

        # knop om geselecteerde reservering te annuleren
        ttk.Button(button_frame, text="Verwijder geselecteerde reservering",
                   command=self.delete_selected_reservation).pack(side="left", padx=5)

        # formulier voor nieuwe reservering
        form = ttk.LabelFrame(tab, text="Nieuwe reservering")
        form.pack(fill="x", padx=5, pady=5)

        ttk.Label(form, text="Klant:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.admin_customer_var = tk.StringVar()
        self.admin_customer_combo = ttk.Combobox(form, textvariable=self.admin_customer_var, state="readonly", width=25)
        self.refresh_admin_customer_combo()
        self.admin_customer_combo.grid(row=0, column=1, padx=5, pady=2)

        ttk.Button(form, text="Nieuwe klant", command=self.new_customer_beheerder) \
            .grid(row=0, column=2, padx=5, pady=2)

        ttk.Label(form, text="Type fiets:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.admin_bike_type_var = tk.StringVar()
        self.admin_bike_type_combo = ttk.Combobox(
            form,
            textvariable=self.admin_bike_type_var,
            values=[b.value for b in BikeType],
            state="readonly",
            width=15,
        )
        self.admin_bike_type_combo.grid(row=1, column=1, padx=5, pady=2)
        self.admin_bike_type_combo.current(0)

        ttk.Label(form, text="Start (YYYY-MM-DD HH:MM):").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.admin_start_entry = ttk.Entry(form, width=20)
        self.admin_start_entry.grid(row=2, column=1, padx=5, pady=2)

        ttk.Label(form, text="Einde (YYYY-MM-DD HH:MM):").grid(row=3, column=0, padx=5, pady=2, sticky="w")
        self.admin_end_entry = ttk.Entry(form, width=20)
        self.admin_end_entry.grid(row=3, column=1, padx=5, pady=2)

        ttk.Label(form, text="Locatie:").grid(row=1, column=2, padx=5, pady=2, sticky="w")
        self.admin_location_var = tk.StringVar(value=LocationType.OPHALEN.value)
        ttk.Radiobutton(form, text="Ophalen", variable=self.admin_location_var,
                        value=LocationType.OPHALEN.value).grid(row=1, column=3, sticky="w")
        ttk.Radiobutton(form, text="Bezorgen", variable=self.admin_location_var,
                        value=LocationType.BEZORGEN.value).grid(row=2, column=3, sticky="w")

        ttk.Label(form, text="Afleveradres (bij bezorgen):").grid(row=3, column=2, padx=5, pady=2, sticky="w")
        self.admin_address_entry = ttk.Entry(form, width=30)
        self.admin_address_entry.grid(row=3, column=3, padx=5, pady=2)

        ttk.Button(form, text="Nieuwe reservering", command=self.create_reservation_beheerder) \
            .grid(row=4, column=0, columnspan=4, pady=5)

        self.refresh_admin_reservations()


        ttk.Label(form, text="Klant:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.admin_customer_var = tk.StringVar()
        self.admin_customer_combo = ttk.Combobox(form, textvariable=self.admin_customer_var, state="readonly", width=25)
        self.refresh_admin_customer_combo()
        self.admin_customer_combo.grid(row=0, column=1, padx=5, pady=2)

        ttk.Button(form, text="Nieuwe klant", command=self.new_customer_beheerder)\
            .grid(row=0, column=2, padx=5, pady=2)

        ttk.Label(form, text="Type fiets:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.admin_bike_type_var = tk.StringVar()
        self.admin_bike_type_combo = ttk.Combobox(
            form,
            textvariable=self.admin_bike_type_var,
            values=[b.value for b in BikeType],
            state="readonly",
            width=15,
        )
        self.admin_bike_type_combo.grid(row=1, column=1, padx=5, pady=2)
        self.admin_bike_type_combo.current(0)

        ttk.Label(form, text="Start (YYYY-MM-DD HH:MM):").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.admin_start_entry = ttk.Entry(form, width=20)
        self.admin_start_entry.grid(row=2, column=1, padx=5, pady=2)

        ttk.Label(form, text="Einde (YYYY-MM-DD HH:MM):").grid(row=3, column=0, padx=5, pady=2, sticky="w")
        self.admin_end_entry = ttk.Entry(form, width=20)
        self.admin_end_entry.grid(row=3, column=1, padx=5, pady=2)

        ttk.Label(form, text="Locatie:").grid(row=1, column=2, padx=5, pady=2, sticky="w")
        self.admin_location_var = tk.StringVar(value=LocationType.OPHALEN.value)
        ttk.Radiobutton(form, text="Ophalen", variable=self.admin_location_var,
                        value=LocationType.OPHALEN.value).grid(row=1, column=3, sticky="w")
        ttk.Radiobutton(form, text="Bezorgen", variable=self.admin_location_var,
                        value=LocationType.BEZORGEN.value).grid(row=2, column=3, sticky="w")

        ttk.Label(form, text="Afleveradres (bij bezorgen):").grid(row=3, column=2, padx=5, pady=2, sticky="w")
        self.admin_address_entry = ttk.Entry(form, width=30)
        self.admin_address_entry.grid(row=3, column=3, padx=5, pady=2)

        ttk.Button(form, text="Nieuwe reservering", command=self.create_reservation_beheerder)\
            .grid(row=4, column=0, columnspan=4, pady=5)

        self.refresh_admin_reservations()

    def refresh_admin_reservations(self):
        reservations = self.store.get_all_reservations()
        for row in self.admin_tree.get_children():
            self.admin_tree.delete(row)
        for r in reservations:
            customer_name = self.store.customers[r.customer_id].name
            self.admin_tree.insert(
                "",
                "end",
                values=(
                    r.reservation_id,
                    customer_name,
                    r.bike_type.value,
                    r.start.strftime("%Y-%m-%d %H:%M"),
                    r.end.strftime("%Y-%m-%d %H:%M"),
                    r.location_type.value,
                    f"{r.total_price:.2f}",
                ),
            )

    def refresh_admin_customer_combo(self):
        values = [f"{c.customer_id} – {c.name}" for c in self.store.customers.values()]
        self.admin_customer_combo["values"] = values
        if values and not self.admin_customer_var.get():
            self.admin_customer_combo.current(0)

    def new_customer_beheerder(self):
        """Nieuwe huurder registreren met wachtwoord (account wordt aangemaakt)."""
        name = simpledialog.askstring("Nieuwe klant", "Naam van de huurder:")
        if not name:
            return

        username = simpledialog.askstring("Nieuwe account", "Gebruikersnaam voor deze huurder:")
        if not username:
            messagebox.showwarning("Geen gebruikersnaam", "Gebruikersnaam is verplicht.")
            return
        if username in self.store.accounts:
            messagebox.showerror("Bestaat al", "Deze gebruikersnaam bestaat al.")
            return

        password = simpledialog.askstring("Nieuwe account", "Wachtwoord voor deze huurder:", show="*")
        if not password:
            messagebox.showwarning("Geen wachtwoord", "Wachtwoord is verplicht.")
            return

        customer = self.store.add_customer(name)
        self.store.add_account(username=username, password=password, role=Role.HUURDER, customer_id=customer.customer_id)

        self.refresh_admin_customer_combo()
        self.refresh_customer_combo()
        messagebox.showinfo("Klant aangemaakt", f"Klant '{name}' met account '{username}' is toegevoegd.")

    def get_admin_selected_customer_id(self):
        value = self.admin_customer_var.get()
        if not value:
            return None
        try:
            return int(value.split("–")[0].strip())
        except Exception:
            return None

    def create_reservation_beheerder(self):
        customer_id = self.get_admin_selected_customer_id()
        if customer_id is None:
            messagebox.showwarning("Geen klant", "Kies of maak eerst een klant.")
            return

        bike_text = self.admin_bike_type_var.get()
        try:
            bike_type = BikeType(bike_text)
        except ValueError:
            messagebox.showerror("Fout", "Ongeldig fietstype.")
            return

        start_text = self.admin_start_entry.get().strip()
        end_text = self.admin_end_entry.get().strip()

        try:
            start_dt = datetime.strptime(start_text, "%Y-%m-%d %H:%M")
            end_dt = datetime.strptime(end_text, "%Y-%m-%d %H:%M")
        except ValueError:
            messagebox.showerror("Fout", "Gebruik formaat: YYYY-MM-DD HH:MM.")
            return

        loc_text = self.admin_location_var.get()
        location = LocationType(loc_text)
        address = self.admin_address_entry.get().strip() if location == LocationType.BEZORGEN else ""

        try:
            res = self.store.create_reservation(
                customer_id=customer_id,
                bike_type=bike_type,
                start=start_dt,
                end=end_dt,
                location_type=location,
                address=address,
            )
        except ValueError as e:
            messagebox.showerror("Fout", str(e))
            return

        messagebox.showinfo(
            "Reservering gemaakt",
            f"Reservering #{res.reservation_id} aangemaakt.\nTotaalprijs: € {res.total_price:.2f}",
        )
        self.refresh_admin_reservations()

    def edit_selected_reservation(self):
        """Open een venster om de geselecteerde reservering te bewerken (datum/locatie/adres)."""
        selected = self.admin_tree.selection()
        if not selected:
            messagebox.showwarning("Geen selectie", "Selecteer eerst een reservering.")
            return
        values = self.admin_tree.item(selected[0], "values")
        res_id = int(values[0])

        if res_id not in self.store.reservations:
            messagebox.showerror("Fout", "Onbekende reservering.")
            return

        r = self.store.reservations[res_id]

        win = tk.Toplevel(self)
        win.title(f"Reservering #{res_id} bewerken")
        win.geometry("420x220")

        ttk.Label(win, text="Start (YYYY-MM-DD HH:MM):").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        start_var = tk.StringVar(value=r.start.strftime("%Y-%m-%d %H:%M"))
        start_entry = ttk.Entry(win, textvariable=start_var, width=22)
        start_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(win, text="Einde (YYYY-MM-DD HH:MM):").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        end_var = tk.StringVar(value=r.end.strftime("%Y-%m-%d %H:%M"))
        end_entry = ttk.Entry(win, textvariable=end_var, width=22)
        end_entry.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(win, text="Locatie:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        loc_var = tk.StringVar(value=r.location_type.value)
        ttk.Radiobutton(win, text="Ophalen", variable=loc_var,
                        value=LocationType.OPHALEN.value).grid(row=2, column=1, sticky="w")
        ttk.Radiobutton(win, text="Bezorgen", variable=loc_var,
                        value=LocationType.BEZORGEN.value).grid(row=3, column=1, sticky="w")

        ttk.Label(win, text="Afleveradres:").grid(row=4, column=0, padx=5, pady=5, sticky="e")
        addr_var = tk.StringVar(value=r.address)
        addr_entry = ttk.Entry(win, textvariable=addr_var, width=30)
        addr_entry.grid(row=4, column=1, padx=5, pady=5)

        def opslaan():
            try:
                new_start = datetime.strptime(start_var.get().strip(), "%Y-%m-%d %H:%M")
                new_end = datetime.strptime(end_var.get().strip(), "%Y-%m-%d %H:%M")
            except ValueError:
                messagebox.showerror("Fout", "Gebruik formaat: YYYY-MM-DD HH:MM.")
                return

            new_loc = LocationType(loc_var.get())
            new_addr = addr_var.get().strip()

            r.start = new_start
            r.end = new_end
            r.location_type = new_loc
            r.address = new_addr

            # prijs opnieuw berekenen
            r.total_price = self.store._calculate_price(r.bike_type, r.start, r.end)

            self.refresh_admin_reservations()
            messagebox.showinfo("Opgeslagen", "Reservering is bijgewerkt.")
            win.destroy()

        ttk.Button(win, text="Opslaan", command=opslaan).grid(row=5, column=0, columnspan=2, pady=10)

    def delete_selected_reservation(self):
        """Verwijder de geselecteerde reservering (voor beheerder)"""
        selected = self.admin_tree.selection()
        if not selected:
            messagebox.showwarning("Geen selectie", "Selecteer eerst een reservering.")
            return
        values = self.admin_tree.item(selected[0], "values")
        res_id = int(values[0])

        bevestigen = messagebox.askyesno(
            "Bevestigen",
            f"Weet je zeker dat je reservering #{res_id} wilt verwijderen?"
        )

        if not bevestigen:
            return

        try:
            self.store.delete_reservation(res_id)
        except ValueError as e:
            messagebox.showerror("Fout", str(e))
            return

        self.refresh_admin_reservations()

        messagebox.showinfo("Verwijdererd", f"Reservering #{res_id} is verwijderd.")

    # --- Fietsen-tab ---

    def build_beheerder_fietsen_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Fietsen")

        frame = ttk.LabelFrame(tab, text="Overzicht fietsen")
        frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.bikes_tree = ttk.Treeview(
            frame,
            columns=("id", "type", "status", "beschikbaar"),
            show="headings",
        )
        headers = ["ID", "Type", "Status", "Beschikbaar"]
        for col, text in zip(("id", "type", "status", "beschikbaar"), headers):
            self.bikes_tree.heading(col, text=text)
            self.bikes_tree.column(col, width=120)
        self.bikes_tree.pack(side="left", fill="both", expand=True)

        scroll = ttk.Scrollbar(frame, orient="vertical", command=self.bikes_tree.yview)
        self.bikes_tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")

        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill="x", padx=5, pady=5)

        ttk.Button(btn_frame, text="Ververs", command=self.refresh_bikes).pack(side="left")
        ttk.Button(btn_frame, text="Markeer geselecteerde fiets als OK", command=self.mark_bike_ok_from_bikes_tab)\
            .pack(side="left", padx=5)

        self.refresh_bikes()

    def refresh_bikes(self):
        for row in self.bikes_tree.get_children():
            self.bikes_tree.delete(row)
        for b in self.store.bikes.values():
            self.bikes_tree.insert(
                "",
                "end",
                values=(
                    b.bike_id,
                    b.bike_type.value,
                    b.status.value,
                    "Ja" if b.available else "Nee",
                ),
            )

    def mark_bike_ok_from_bikes_tab(self):
        selected = self.bikes_tree.selection()
        if not selected:
            messagebox.showwarning("Geen selectie", "Selecteer eerst een fiets.")
            return
        values = self.bikes_tree.item(selected[0], "values")
        bike_id = int(values[0])
        bike = self.store.bikes.get(bike_id)
        if not bike:
            messagebox.showerror("Fout", "Onbekende fiets.")
            return
        bike.status = BikeStatus.OK
        bike.available = True
        self.refresh_bikes()

    # ========== Monteur-scherm ==========

    def build_monteur_screen(self):
        frame = ttk.Frame(self.main_frame)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        rep_frame = ttk.LabelFrame(frame, text="Reparatie-opdrachten")
        rep_frame.pack(fill="both", expand=True, pady=5)

        self.rep_tree = ttk.Treeview(
            rep_frame,
            columns=("id", "bike", "res", "defect"),
            show="headings",
        )
        headers = ["#", "Fiets", "Reservering", "Defect"]
        for col, text in zip(("id", "bike", "res", "defect"), headers):
            self.rep_tree.heading(col, text=text)
            self.rep_tree.column(col, width=140)
        self.rep_tree.pack(side="left", fill="both", expand=True)

        scroll = ttk.Scrollbar(rep_frame, orient="vertical", command=self.rep_tree.yview)
        self.rep_tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=5)

        ttk.Button(btn_frame, text="Ververs", command=self.refresh_repairs_tree).pack(side="left")
        ttk.Button(btn_frame, text="Fiets gerepareerd (OK maken)", command=self.fix_bike_from_selected_repair)\
            .pack(side="left", padx=5)

        self.refresh_repairs_tree()

    def refresh_repairs_tree(self):
        for row in self.rep_tree.get_children():
            self.rep_tree.delete(row)
        for rep in self.store.get_all_repairs():
            self.rep_tree.insert(
                "",
                "end",
                values=(
                    rep.repair_id,
                    rep.bike_id,
                    rep.reservation_id,
                    f"{rep.defect_type}: {rep.description}",
                ),
            )

    def fix_bike_from_selected_repair(self):
        selected = self.rep_tree.selection()
        if not selected:
            messagebox.showwarning("Geen selectie", "Selecteer eerst een reparatie.")
            return
        values = self.rep_tree.item(selected[0], "values")
        repair_id = int(values[0])
        try:
            self.store.fix_bike_from_repair(repair_id)
        except ValueError as e:
            messagebox.showerror("Fout", str(e))
            return
        messagebox.showinfo("Succes", "Fiets is gemarkeerd als OK en beschikbaar.")
        self.refresh_repairs_tree()

    # ---------- sluiten ----------

    def on_close(self):
        try:
            self.store.save_to_csv(".")
        except Exception as e:
            print("Fout bij opslaan:", e)
        self.destroy()


if __name__ == "__main__":
    app = BikerApp()
    app.mainloop()
