import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime

from model import DataStore, BikeType, LocationType, Role, BikeStatus


class BikerApp(tk.Tk):
    """
    Eenvoudige Tkinter GUI met inloggen per rol.
    - Inlogscherm (rol + gebruikersnaam/wachtwoord)
    - Huurder: eigen reserveringen + formulier 'Nieuwe reservering' + Uitloggen
    - Beheerder: Notebook met tab 'Bestellingen' en tab 'Fietsen'
    - Monteur: overzicht reparaties + knop 'Fiets gerepareerd' + Uitloggen
    """

    def __init__(self):
        super().__init__()

        self.title("BIKER – eenvoudige desktopapplicatie")
        self.geometry("900x550")

        self.store = DataStore()
        self.store.load_from_csv(".")   # data laden uit CSV (indien aanwezig)

        # demo-data aanmaken als er nog niets is
        self.ensure_demo_data()

        self.current_account = None
        self.current_role: Role | None = None

        # inlogscherm
        self.login_frame = ttk.Frame(self)
        self.build_login_frame()
        self.login_frame.pack(fill="both", expand=True)

        # hoofd-UI (wordt aangemaakt na inloggen)
        self.main_frame = None
        self.notebook = None

        # bij sluiten van de applicatie: data opslaan
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------- DEMO-DATA ----------

    def ensure_demo_data(self):
        """Zorgt dat er minimaal een paar klanten, fietsen en accounts zijn."""
        # klanten
        if not self.store.customers:
            c1 = self.store.add_customer("Dima")
            c2 = self.store.add_customer("Anna")
        else:
            c1 = list(self.store.customers.values())[0]

        # fietsen – als er nog geen zijn, maak 10 standaard fietsen
        if not self.store.bikes:
            # 5 stadsfietsen
            for _ in range(5):
                self.store.add_bike(BikeType.STADSFIETS, BikeStatus.OK)
            # 5 e-bikes
            for _ in range(5):
                self.store.add_bike(BikeType.E_BIKE, BikeStatus.OK)

        # accounts
        if not self.store.accounts:
            # Huurder gekoppeld aan klant c1
            self.store.add_account("huur1", "test", Role.HUURDER, customer_id=c1.customer_id)
            # Beheerder
            self.store.add_account("admin1", "admin", Role.BEHEERDER)
            # Monteur
            self.store.add_account("monteur1", "monteur", Role.MONTEUR)

    # ---------- INLOG-UI ----------

    def build_login_frame(self):
        """Maakt het inlogscherm."""
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
            text=(
                "Demo-accounts:\n"
                "Huurder:  huur1 / test\n"
                "Beheerder: admin1 / admin\n"
                "Monteur:  monteur1 / monteur"
            ),
            foreground="gray",
        )
        hint.pack(pady=5)

    def handle_login(self):
        """Verwerkt de inlogpoging van de gebruiker."""
        role_text = self.role_var.get()
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        if not username or not password:
            messagebox.showwarning("Ontbrekende gegevens", "Vul gebruikersnaam en wachtwoord in.")
            return

        role = Role(role_text)
        acc = self.store.authenticate(username, password, role)
        if acc is None:
            messagebox.showerror(
                "Inloggen mislukt",
                "Onjuiste combinatie van rol / gebruikersnaam / wachtwoord."
            )
            return

        self.current_account = acc
        self.current_role = role

        # verberg het inlogscherm
        self.login_frame.pack_forget()

        # bouw de hoofd-UI op basis van de rol
        self.build_main_ui()

    # ---------- HOOFD-UI NA INLOGGEN ----------

    def build_main_ui(self):
        """Maakt het hoofdscherm na succesvol inloggen."""
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill="both", expand=True)

        # bovenste balk met info + Uitloggen-knop
        top = ttk.Frame(self.main_frame)
        top.pack(fill="x", padx=10, pady=5)

        ttk.Label(
            top,
            text=f"Ingelogd als: {self.current_role.value} ({self.current_account.username})",
            font=("Arial", 10, "bold")
        ).pack(side="left")

        ttk.Button(top, text="Uitloggen", command=self.logout).pack(side="right")

        # toon scherm afhankelijk van rol
        if self.current_role == Role.HUURDER:
            self.build_huurder_screen()
        elif self.current_role == Role.BEHEERDER:
            self.build_beheerder_screen()
        elif self.current_role == Role.MONTEUR:
            self.build_monteur_screen()

    def clear_main_content(self):
        """Verwijdert het huidige hoofdscherm (bijv. bij uitloggen)."""
        if self.main_frame is not None:
            self.main_frame.destroy()
            self.main_frame = None
            self.notebook = None

    def logout(self):
        """Logt de gebruiker uit en keert terug naar het inlogscherm."""
        self.current_account = None
        self.current_role = None
        self.clear_main_content()
        self.login_frame.pack(fill="both", expand=True)

    # ========== SCHERM HUURDER ==========

    def build_huurder_screen(self):
        """Bouwt het scherm voor de rol Huurder."""
        frame = ttk.Frame(self.main_frame)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        # extra knop bovenaan om een reservering aan te maken
        ttk.Button(frame, text="Nieuwe reservering", command=self.create_reservation)\
            .pack(anchor="w", pady=(0, 5))

        # klantselectie (voor Huurder eigenlijk vast, via account.customer_id)
        klant_frame = ttk.Frame(frame)
        klant_frame.pack(fill="x", pady=5)

        ttk.Label(klant_frame, text="Klant:").pack(side="left")
        self.customer_var = tk.StringVar()
        self.customer_combo = ttk.Combobox(klant_frame, textvariable=self.customer_var, state="readonly")
        self.refresh_customer_combo()
        self.customer_combo.pack(side="left", padx=5)

        if self.current_role == Role.HUURDER and self.current_account.customer_id is not None:
            # stel de juiste klant in en maak de combobox niet wijzigbaar
            cust_id = self.current_account.customer_id
            for i, c in enumerate(self.store.customers.values()):
                if c.customer_id == cust_id:
                    self.customer_combo.current(i)
                    break
            self.customer_combo.configure(state="disabled")

        ttk.Button(klant_frame, text="Toon mijn reserveringen", command=self.show_customer_reservations)\
            .pack(side="left", padx=5)

        # overzicht van reserveringen
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
        self.res_tree.configure(yscroll=scroll.set)
        scroll.pack(side="right", fill="y")

        # formulier voor nieuwe reservering
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

        # formulier voor defectmelding
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

    # --- helpers Huurder / algemeen ---

    def refresh_customer_combo(self):
        """Vult de klant-combobox (voor Huurder-scherm)."""
        values = [f"{c.customer_id} – {c.name}" for c in self.store.customers.values()]
        self.customer_combo["values"] = values
        if values and not self.customer_var.get():
            self.customer_combo.current(0)

    def get_selected_customer_id(self):
        """Geeft het geselecteerde klantnummer terug, of dat van de ingelogde huurder."""
        if self.current_role == Role.HUURDER and self.current_account.customer_id is not None:
            return self.current_account.customer_id

        value = self.customer_var.get()
        if not value:
            return None
        try:
            id_part = value.split("–")[0].strip()
            return int(id_part)
        except Exception:
            return None

    def show_customer_reservations(self):
        """Toont alle reserveringen van de geselecteerde klant in de tabel."""
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
        """Maakt een nieuwe reservering aan (vanuit Huurder-scherm)."""
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
        """Maakt een reparatiemelding op basis van een reserveringsnummer."""
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
            repair = self.store.report_defect(
                reservation_id=res_id,
                defect_type=defect_type,
                description=description
            )
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

    # ========== SCHERM BEHEERDER ==========

    def build_beheerder_screen(self):
        """Bouwt het scherm voor de rol Beheerder met een Notebook."""
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.build_beheerder_bestellingen_tab()
        self.build_beheerder_fietsen_tab()

    def build_beheerder_bestellingen_tab(self):
        """Tab 'Bestellingen' met alle reserveringen en formulier 'Nieuwe reservering'."""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Bestellingen")

        top = ttk.Frame(tab)
        top.pack(fill="x", pady=5)
        ttk.Button(top, text="Nieuwe reservering", command=self.create_reservation_beheerder)\
            .pack(side="left", padx=5)

        # overzicht van alle reserveringen
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
        self.admin_tree.configure(yscroll=scroll.set)
        scroll.pack(side="right", fill="y")

        # formulier nieuwe reservering (met klantkeuze en 'Nieuwe klant'-knop)
        form = ttk.LabelFrame(tab, text="Nieuwe reservering")
        form.pack(fill="x", padx=5, pady=5)

        ttk.Label(form, text="Klant:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.admin_customer_var = tk.StringVar()
        self.admin_customer_combo = ttk.Combobox(
            form,
            textvariable=self.admin_customer_var,
            state="readonly",
            width=25
        )
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
        """Vult de tabel met alle reserveringen (voor Beheerder)."""
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
        """Vult de klant-combobox in het Beheerder-scherm."""
        values = [f"{c.customer_id} – {c.name}" for c in self.store.customers.values()]
        self.admin_customer_combo["values"] = values
        if values and not self.admin_customer_var.get():
            self.admin_customer_combo.current(0)

    def new_customer_beheerder(self):
        """Laat de beheerder een nieuwe klant aanmaken (via dialoog)."""
        name = simpledialog.askstring("Nieuwe klant", "Naam van de klant:")
        if not name:
            return
        self.store.add_customer(name)
        self.refresh_admin_customer_combo()
        # ook handig voor Huurder-combobox als je later wisselt van rol
        # (hier wordt alleen de Beheerder-combobox opnieuw gevuld)

    def get_admin_selected_customer_id(self):
        """Geeft het klantnummer terug dat in de Beheerder-klant-combobox gekozen is."""
        value = self.admin_customer_var.get()
        if not value:
            return None
        try:
            return int(value.split("–")[0].strip())
        except Exception:
            return None

    def create_reservation_beheerder(self):
        """Maakt een nieuwe reservering aan via het Beheerder-scherm."""
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

    # --- Tab 'Fietsen' ---

    def build_beheerder_fietsen_tab(self):
        """Tab 'Fietsen' met status van alle fietsen."""
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
        self.bikes_tree.configure(yscroll=scroll.set)
        scroll.pack(side="right", fill="y")

        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill="x", padx=5, pady=5)

        ttk.Button(btn_frame, text="Ververs", command=self.refresh_bikes).pack(side="left")
        ttk.Button(
            btn_frame,
            text="Markeer geselecteerde fiets als OK",
            command=self.mark_bike_ok_from_bikes_tab
        ).pack(side="left", padx=5)

        self.refresh_bikes()

    def refresh_bikes(self):
        """Vult de tabel met alle fietsen en hun status."""
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
        """Zet de geselecteerde fiets in de tab 'Fietsen' op status OK en beschikbaar."""
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

    # ========== SCHERM MONTEUR ==========

    def build_monteur_screen(self):
        """Bouwt het scherm voor de rol Monteur met reparatie-overzicht."""
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
        self.rep_tree.configure(yscroll=scroll.set)
        scroll.pack(side="right", fill="y")

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=5)

        ttk.Button(btn_frame, text="Ververs", command=self.refresh_repairs_tree).pack(side="left")
        ttk.Button(
            btn_frame,
            text="Fiets gerepareerd (OK maken)",
            command=self.fix_bike_from_selected_repair
        ).pack(side="left", padx=5)

        self.refresh_repairs_tree()

    def refresh_repairs_tree(self):
        """Vult de tabel met alle reparaties."""
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
        """Markeert de fiets van de geselecteerde reparatie als OK en beschikbaar."""
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

    # ---------- AFSLUITEN ----------

    def on_close(self):
        """Wordt aangeroepen bij afsluiten van het hoofdvenster: slaat data op en sluit."""
        try:
            self.store.save_to_csv(".")
        except Exception as e:
            print("Fout bij opslaan:", e)
        self.destroy()


if __name__ == "__main__":
    app = BikerApp()
    app.mainloop()
