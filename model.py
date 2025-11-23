from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import csv
import os


# ===== ENUMS =====

class BikeType(Enum):
    STADSFIETS = "Stadsfiets"
    E_BIKE = "E-bike"


class LocationType(Enum):
    OPHALEN = "Ophalen"
    BEZORGEN = "Bezorgen"


class Role(Enum):
    HUURDER = "Huurder"
    BEHEERDER = "Beheerder"
    MONTEUR = "Monteur"


class BikeStatus(Enum):
    OK = "OK"
    DEFECT = "Defect"

class ReservationStatus(Enum):
    GEPLAND = "Gepland"
    LOPEND = "Lopend"
    AFGEROND = "Afgerond"
    GEANNULEERD = "Geannuleerd"

# ===== DATAKLASSEN =====

@dataclass
class Customer:
    customer_id: int
    name: str
    email: str =""
    iban: str = ""
    delivery_address: str = ""




@dataclass
class Bike:
    bike_id: int
    bike_type: BikeType
    status: BikeStatus = BikeStatus.OK
    available: bool = True


@dataclass
class Reservation:
    reservation_id: int
    customer_id: int
    bike_id: int
    bike_type: BikeType
    start: datetime
    end: datetime
    location_type: LocationType
    address: str = ""
    status: ReservationStatus = ReservationStatus.GEPLAND
    total_price: float = 0.0


@dataclass
class Repair:
    repair_id: int
    reservation_id: int
    bike_id: int
    defect_type: str
    description: str


@dataclass
class UserAccount:
    username: str
    password: str
    role: Role
    customer_id: int | None = None    # alleen voor Huurder


# ===== BACKEND met CSV =====

class DataStore:
    """
    in-memory backend.
    Behouden klaanten, fietsen, reservaties, reparaties en accounts.
    import/ export CSV
    """

    # prijces
    BASE_PRICE_PER_DAY = {
        BikeType.STADSFIETS: 15.0,
        BikeType.E_BIKE: 25.0,
    }

    DATETIME_FORMAT = "%Y-%m-%d %H:%M"

    def __init__(self):
        self.customers: dict[int, Customer] = {}
        self.bikes: dict[int, Bike] = {}
        self.reservations: dict[int, Reservation] = {}
        self.repairs: dict[int, Repair] = {}
        self.accounts: dict[str, UserAccount] = {}

        self.next_customer_id = 1
        self.next_bike_id = 1
        self.next_reservation_id = 1
        self.next_repair_id = 1

    # --- klanten ---

    def add_customer(
            self,
            name: str,
            email: str = "",
            iban: str = "",
            delivery_address: str = "",
    ) -> Customer:
        """voeg een nieuwe klant toe"""
        customer = Customer(
            customer_id=self.next_customer_id,
            name=name,
            email = email,
            iban = iban,
            delivery_address = delivery_address
        )
        self.customers[self.next_customer_id] = customer
        self.next_customer_id += 1
        return customer

    # --- fietsen ---

    def add_bike(self, bike_type: BikeType, status: BikeStatus = BikeStatus.OK) -> Bike:
        bike = Bike(
            bike_id=self.next_bike_id,
            bike_type=bike_type,
            status=status,
            available=True,
        )
        self.bikes[self.next_bike_id] = bike
        self.next_bike_id += 1
        return bike

    def get_available_bike(self, bike_type: BikeType):
        """Returns available bike status for given bike_type."""
        for bike in self.bikes.values():
            if (
                bike.bike_type == bike_type
                and bike.status == BikeStatus.OK
                and bike.available
            ):
                return bike
        return None

    # --- reservaties ---

    def _calculate_price(self, bike_type: BikeType, start: datetime, end: datetime) -> float:
        """Prijs berekening."""
        base_price = self.BASE_PRICE_PER_DAY[bike_type]
        delta = end - start
        days = delta.days
        if days <= 0:
            days = 1
        return round(base_price * days, 2)

    def create_reservation(
        self,
        customer_id: int,
        bike_type: BikeType,
        start: datetime,
        end: datetime,
        location_type: LocationType,
        address: str = "",
    ) -> Reservation:
        if customer_id not in self.customers:
            raise ValueError("Onbekende klant.")

        bike = self.get_available_bike(bike_type)
        if bike is None:
            raise ValueError("Geen beschikbare fiets van dit type (OK en vrij).")

        price = self._calculate_price(bike_type, start, end)

        reservation = Reservation(
            reservation_id=self.next_reservation_id,
            customer_id=customer_id,
            bike_id=bike.bike_id,
            bike_type=bike_type,
            start=start,
            end=end,
            location_type=location_type,
            address=address if location_type == LocationType.BEZORGEN else "",
            status=ReservationStatus.GEPLAND,
            total_price=price,
        )

        bike.available = False
        self.reservations[self.next_reservation_id] = reservation
        self.next_reservation_id += 1
        return reservation

    def get_reservations_for_customer(self, customer_id: int, only_current_and_future: bool = True):
        """
        Geeft reserveringen voor deze klant.
        Standaard alleen actuele en toekomstige reserveringen (US3).
        """
        now = datetime.now()
        result = []
        for r in self.reservations.values():
            if r.customer_id != customer_id:
                continue
            # alleen actuele en toekomstige reserveringen:
            # - toekomstige: r.end > nu
            # - lopend: r.start <= nu <= r.end
            if only_current_and_future:
                if r.end < now:
                    continue
            result.append(r)

        return result

    def get_all_reservations(self):
        return list(self.reservations.values())

    def delete_reservation(self, reservation_id: int):
        """Verwijdert een reservering en maak gekoppelde fiets weer beschikbaar"""
        if reservation_id not in self.reservations:
            raise ValueError("Onbekende reservering.")

        res = self.reservations.pop(reservation_id)

        # gekoppelde fiets weer vrijgeven (indien bekend)
        if res.bike_id in self.bikes:
            bike = self.bikes[res.bike_id]
    #         alleen vrijgeven als de fiets niet defect is
            if bike.status == BikeStatus.OK:
                bike.available = True

    # --- reparaties ---

    def report_defect(self, reservation_id: int, defect_type: str, description: str) -> Repair:
        if reservation_id not in self.reservations:
            raise ValueError("Onbekende reservering.")

        reservation = self.reservations[reservation_id]
        bike = self.bikes[reservation.bike_id]

        repair = Repair(
            repair_id=self.next_repair_id,
            reservation_id=reservation.reservation_id,
            bike_id=bike.bike_id,
            defect_type=defect_type,
            description=description,
        )

        # fiets markeren als deffect of onbereikbaar
        bike.status = BikeStatus.DEFECT
        bike.available = False

        self.repairs[self.next_repair_id] = repair
        self.next_repair_id += 1
        return repair

    def get_all_repairs(self):
        return list(self.repairs.values())

    def fix_bike_from_repair(self, repair_id: int):
        """Простая логика для Monteur: по repair_id пометить велосипед как OK и доступный."""
        if repair_id not in self.repairs:
            raise ValueError("Onbekende reparatie.")
        repair = self.repairs[repair_id]
        bike_id = repair.bike_id
        if bike_id not in self.bikes:
            raise ValueError("Onbekende fiets.")
        bike = self.bikes[bike_id]
        bike.status = BikeStatus.OK
        bike.available = True

    # --- accounts / login ---

    def add_account(
        self,
        username: str,
        password: str,
        role: Role,
        customer_id: int | None = None,
    ) -> UserAccount:
        acc = UserAccount(username=username, password=password, role=role, customer_id=customer_id)
        self.accounts[username] = acc
        return acc

    def authenticate(self, username: str, password: str, role: Role):
        acc = self.accounts.get(username)
        if acc is None:
            return None
        if acc.password != password:
            return None
        if acc.role != role:
            return None
        return acc

    # ====== CSV: opslaan en import ======

    def save_to_csv(self, folder: str = "."):
        os.makedirs(folder, exist_ok=True)
        self._save_customers_csv(os.path.join(folder, "customers.csv"))
        self._save_bikes_csv(os.path.join(folder, "bikes.csv"))
        self._save_reservations_csv(os.path.join(folder, "reservations.csv"))
        self._save_repairs_csv(os.path.join(folder, "repairs.csv"))
        self._save_accounts_csv(os.path.join(folder, "accounts.csv"))

    def load_from_csv(self, folder: str = "."):
        self.customers.clear()
        self.bikes.clear()
        self.reservations.clear()
        self.repairs.clear()
        self.accounts.clear()

        self.next_customer_id = 1
        self.next_bike_id = 1
        self.next_reservation_id = 1
        self.next_repair_id = 1

        self._load_customers_csv(os.path.join(folder, "customers.csv"))
        self._load_bikes_csv(os.path.join(folder, "bikes.csv"))
        self._load_reservations_csv(os.path.join(folder, "reservations.csv"))
        self._load_repairs_csv(os.path.join(folder, "repairs.csv"))
        self._load_accounts_csv(os.path.join(folder, "accounts.csv"))

    # --- CSV: customers ---

    def _save_customers_csv(self, filename: str):
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["customer_id", "name", "email", "iban", "delivery_address"])
            for c in self.customers.values():
                writer.writerow([c.customer_id, c.name, c.email, c.iban, c.delivery_address])

    def _load_customers_csv(self, filename: str):
        if not os.path.exists(filename):
            return
        max_id = 0
        with open(filename, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cid = int(row["customer_id"])
                name = row["name"]
                email = row.get("name", "")
                iban = row.get("iban", "")
                delivery_address = row.get("delivery_address", "")

                self.customers[cid] = Customer(
                    customer_id=cid,
                    name=name,
                    email = email,
                    iban = iban,
                    delivery_address = delivery_address,
                )

                if cid > max_id:
                    max_id = cid
        self.next_customer_id = max_id + 1

    # --- CSV: bikes ---

    def _save_bikes_csv(self, filename: str):
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["bike_id", "bike_type", "status", "available"])
            for b in self.bikes.values():
                writer.writerow([
                    b.bike_id,
                    b.bike_type.name,
                    b.status.name,
                    int(b.available),
                ])

    def _load_bikes_csv(self, filename: str):
        if not os.path.exists(filename):
            return
        max_id = 0
        with open(filename, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                bid = int(row["bike_id"])
                bike_type_name = row["bike_type"]
                status_name = row["status"]
                available = bool(int(row["available"]))
                bike_type = BikeType[bike_type_name]
                status = BikeStatus[status_name]
                self.bikes[bid] = Bike(
                    bike_id=bid,
                    bike_type=bike_type,
                    status=status,
                    available=available,
                )
                if bid > max_id:
                    max_id = bid
        self.next_bike_id = max_id + 1

    # --- CSV: reservations ---

    def _save_reservations_csv(self, filename: str):
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "reservation_id",
                "customer_id",
                "bike_id",
                "bike_type",
                "start",
                "end",
                "location_type",
                "address",
                "status",
                "total_price",
            ])
            for r in self.reservations.values():
                writer.writerow([
                    r.reservation_id,
                    r.customer_id,
                    r.bike_id,
                    r.bike_type.name,
                    r.start.strftime(self.DATETIME_FORMAT),
                    r.end.strftime(self.DATETIME_FORMAT),
                    r.location_type.name,
                    r.address,
                    r.status.name,
                    r.total_price,
                ])

    def _load_reservations_csv(self, filename: str):
        if not os.path.exists(filename):
            return
        max_id = 0
        with open(filename, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            has_status = "status" in fieldnames

            for row in reader:
                rid = int(row["reservation_id"])
                customer_id = int(row["customer_id"])
                bike_id = int(row["bike_id"])
                bike_type = BikeType[row["bike_type"]]
                start = datetime.strptime(row["start"], self.DATETIME_FORMAT)
                end = datetime.strptime(row["end"], self.DATETIME_FORMAT)
                location_type = LocationType[row["location_type"]]
                address = row["address"]

                total_price = float(row["total_price"])

                # Voor oude CSV-bestanden zonder 'status'-kolom:
                if has_status:
                    status_name = row.get("status") or "GEPLAND"
                    status = ReservationStatus[status_name]
                else:
                    status = ReservationStatus.GEPLAND

                self.reservations[rid] = Reservation(
                    reservation_id=rid,
                    customer_id=customer_id,
                    bike_id=bike_id,
                    bike_type=bike_type,
                    start=start,
                    end=end,
                    location_type=location_type,
                    address=address,
                    status=status,
                    total_price=total_price,
                )

                if rid > max_id:
                    max_id = rid
        self.next_reservation_id = max_id + 1

    # --- CSV: repairs ---

    def _save_repairs_csv(self, filename: str):
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "repair_id",
                "reservation_id",
                "bike_id",
                "defect_type",
                "description",
            ])
            for rep in self.repairs.values():
                writer.writerow([
                    rep.repair_id,
                    rep.reservation_id,
                    rep.bike_id,
                    rep.defect_type,
                    rep.description,
                ])

    def _load_repairs_csv(self, filename: str):
        if not os.path.exists(filename):
            return
        max_id = 0
        with open(filename, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rep_id = int(row["repair_id"])
                reservation_id = int(row["reservation_id"])
                bike_id = int(row["bike_id"])
                defect_type = row["defect_type"]
                description = row["description"]

                self.repairs[rep_id] = Repair(
                    repair_id=rep_id,
                    reservation_id=reservation_id,
                    bike_id=bike_id,
                    defect_type=defect_type,
                    description=description,
                )
                if rep_id > max_id:
                    max_id = rep_id
        self.next_repair_id = max_id + 1

    # --- CSV: accounts ---

    def _save_accounts_csv(self, filename: str):
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["username", "password", "role", "customer_id"])
            for acc in self.accounts.values():
                writer.writerow([
                    acc.username,
                    acc.password,
                    acc.role.name,
                    acc.customer_id if acc.customer_id is not None else "",
                ])

    def _load_accounts_csv(self, filename: str):
        if not os.path.exists(filename):
            return
        with open(filename, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                username = row["username"]
                password = row["password"]
                role = Role[row["role"]]
                cust_id_str = row["customer_id"]
                customer_id = int(cust_id_str) if cust_id_str else None
                self.accounts[username] = UserAccount(
                    username=username,
                    password=password,
                    role=role,
                    customer_id=customer_id,
                )
