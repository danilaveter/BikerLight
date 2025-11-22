import unittest
import tempfile
import os
from datetime import datetime, timedelta

from model import (
    DataStore,
    BikeType,
    LocationType,
    Role,
    BikeStatus,
)


class TestBikerDataStore(unittest.TestCase):
    """
    Unit tests voor de backend-logica (DataStore).
    """

    def setUp(self):
        # tijdelijk mapje voor CSV voor elke test
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.folder = self.tmp_dir.name
        self.store = DataStore()

    def tearDown(self):
        self.tmp_dir.cleanup()

    # TST-01: Inloggen huurder – geldig account
    def test_login_valid_customer(self):
        # Arrange
        cust = self.store.add_customer("Dima", email="dima@example.com")
        self.store.add_account(
            username="dima",
            password="test",
            role=Role.HUURDER,
            customer_id=cust.customer_id,
        )

        # Act
        acc = self.store.authenticate("dima", "test", Role.HUURDER)

        # Assert
        self.assertIsNotNone(acc)
        self.assertEqual(acc.username, "dima")
        self.assertEqual(acc.role, Role.HUURDER)
        self.assertEqual(acc.customer_id, cust.customer_id)

    # TST-02: Inloggen huurder – ongeldig wachtwoord
    def test_login_invalid_password(self):
        # Arrange
        cust = self.store.add_customer("Dima", email="dima@example.com")
        self.store.add_account(
            username="dima",
            password="test",
            role=Role.HUURDER,
            customer_id=cust.customer_id,
        )

        # Act
        acc = self.store.authenticate("dima", "fout", Role.HUURDER)

        # Assert
        self.assertIsNone(acc)

    # TST-03: Nieuwe reservering aanmaken (Huurder)
    def test_create_reservation(self):
        # Arrange
        cust = self.store.add_customer("Anna", email="anna@example.com")
        bike = self.store.add_bike(BikeType.STADSFIETS)

        start = datetime(2025, 1, 1, 10, 0)
        end = datetime(2025, 1, 2, 10, 0)  # precies 1 dag
        # Act
        res = self.store.create_reservation(
            customer_id=cust.customer_id,
            bike_type=BikeType.STADSFIETS,
            start=start,
            end=end,
            location_type=LocationType.OPHALEN,
        )

        # Assert
        self.assertEqual(res.customer_id, cust.customer_id)
        self.assertEqual(res.bike_id, bike.bike_id)
        self.assertEqual(res.bike_type, BikeType.STADSFIETS)
        self.assertEqual(res.total_price, 15.0)  # 1 dag stadsfiets = 15
        self.assertFalse(self.store.bikes[bike.bike_id].available)

    # Extra: reserveringen voor klant ophalen
    def test_get_reservations_for_customer(self):
        cust1 = self.store.add_customer("Klant 1")
        cust2 = self.store.add_customer("Klant 2")
        self.store.add_bike(BikeType.STADSFIETS)
        self.store.add_bike(BikeType.STADSFIETS)

        start = datetime(2025, 1, 1, 10, 0)
        end = datetime(2025, 1, 2, 10, 0)

        self.store.create_reservation(
            customer_id=cust1.customer_id,
            bike_type=BikeType.STADSFIETS,
            start=start,
            end=end,
            location_type=LocationType.OPHALEN,
        )
        self.store.create_reservation(
            customer_id=cust2.customer_id,
            bike_type=BikeType.STADSFIETS,
            start=start,
            end=end,
            location_type=LocationType.OPHALEN,
        )

        res_c1 = self.store.get_reservations_for_customer(cust1.customer_id)
        res_c2 = self.store.get_reservations_for_customer(cust2.customer_id)

        self.assertEqual(len(res_c1), 1)
        self.assertEqual(len(res_c2), 1)
        self.assertNotEqual(res_c1[0].customer_id, res_c2[0].customer_id)

    # TST-05: Klantgegevens opslaan in customers.csv
    def test_customer_saved_to_csv(self):
        # Arrange
        cust = self.store.add_customer(
            name="Darian",
            email="darian@example.com",
            iban="NL00TEST0123456789",
            delivery_address="Straat 1",
        )

        # Act
        self.store.save_to_csv(self.folder)

        # Nieuwe DataStore inlezen uit CSV
        new_store = DataStore()
        new_store.load_from_csv(self.folder)

        # Assert
        self.assertIn(cust.customer_id, new_store.customers)
        new_cust = new_store.customers[cust.customer_id]
        self.assertEqual(new_cust.name, "Darian")
        # iban moet meegeschreven worden
        self.assertEqual(new_cust.iban, "NL00TEST0123456789")

    # TST-06: Klantgegevens bijwerken (profiel -> CSV update)
    def test_update_customer_and_save_to_csv(self):
        # Arrange
        cust = self.store.add_customer(
            name="Dima",
            email="dima@example.com",
            iban="OUDEIBAN",
            delivery_address="Oud adres",
        )
        self.store.save_to_csv(self.folder)

        # Update klantgegevens in memory
        cust.iban = "NIEUWEIBAN"
        cust.delivery_address = "Nieuw adres"

        # Act
        self.store.save_to_csv(self.folder)

        # Nieuwe DataStore inlezen
        new_store = DataStore()
        new_store.load_from_csv(self.folder)

        # Assert
        new_cust = new_store.customers[cust.customer_id]
        self.assertEqual(new_cust.iban, "NIEUWEIBAN")
        self.assertEqual(new_cust.delivery_address, "Nieuw adres")

    # TST-07: Reparatiestatus bijwerken (Monteur)
    def test_report_defect_and_fix_bike(self):
        # Arrange: klant + fiets + reservering
        cust = self.store.add_customer("Monteur test")
        bike = self.store.add_bike(BikeType.E_BIKE)

        start = datetime(2025, 1, 1, 10, 0)
        end = datetime(2025, 1, 2, 10, 0)
        res = self.store.create_reservation(
            customer_id=cust.customer_id,
            bike_type=BikeType.E_BIKE,
            start=start,
            end=end,
            location_type=LocationType.OPHALEN,
        )

        # Act: defect melden
        repair = self.store.report_defect(
            reservation_id=res.reservation_id,
            defect_type="Lekke band",
            description="Achterband is lek.",
        )

        # Assert: fiets moet defect & niet beschikbaar zijn
        bike_after_defect = self.store.bikes[bike.bike_id]
        self.assertEqual(bike_after_defect.status, BikeStatus.DEFECT)
        self.assertFalse(bike_after_defect.available)

        # Act 2: monteur fixt de fiets
        self.store.fix_bike_from_repair(repair.repair_id)

        # Assert 2: fiets weer OK en beschikbaar
        bike_fixed = self.store.bikes[bike.bike_id]
        self.assertEqual(bike_fixed.status, BikeStatus.OK)
        self.assertTrue(bike_fixed.available)

    # Extra: reservering verwijderen maakt fiets weer beschikbaar
    def test_delete_reservation_makes_bike_available(self):
        cust = self.store.add_customer("Test")
        bike = self.store.add_bike(BikeType.STADSFIETS)
