
import unittest
from copy import deepcopy

from eco_core import (
    DEFAULT,
    FACTORS,
    calculate,
    scenario,
    biomass_factor,
    WOOD_NCV,
)


def empty_profile():
    """Sıfır tüketimli geçerli test profili."""
    d = deepcopy(DEFAULT)

    for key in d:
        if key in ("car_fuel", "boat_fuel"):
            continue

        if key in (
            "bus_occupancy",
            "fertilizer_bag_kg",
            "fertilizer_n_fraction",
            "fertilizer_ef_n2o",
        ):
            continue

        d[key] = 0.0

    return d


class EcoAlgoritmaTests(unittest.TestCase):

    def test_01_zero_consumption(self):
        d = empty_profile()
        r = calculate(d)

        self.assertAlmostEqual(r["base"], 0)
        self.assertAlmostEqual(r["expanded"], 0)
        self.assertAlmostEqual(r["local"], 0)
        self.assertIsNone(r["local_percent"])

    def test_02_basic_expanded_model(self):
        d = empty_profile()
        d["electric_kwh"] = 1000
        d["wood_kg"] = 100

        r = calculate(d)

        expected_electric = 1000 * 0.469
        expected_wood = 100 * biomass_factor(WOOD_NCV)

        self.assertAlmostEqual(
            r["base"],
            expected_electric,
            places=6
        )

        self.assertAlmostEqual(
            r["expanded"],
            expected_electric + expected_wood,
            places=6
        )

        self.assertAlmostEqual(
            r["local"],
            expected_wood,
            places=6
        )

    def test_03_boat_and_fertilizer(self):
        d = empty_profile()

        d["boat_fuel"] = "Dizel"
        d["boat_l_week"] = 10
        d["boat_weeks"] = 20
        d["fertilizer_bags"] = 2

        r = calculate(d)

        boat = 10 * 20 * 2.58354

        fertilizer = (
            2 * 50 * 0.20 * 0.010
            * (44 / 28) * 265
        )

        self.assertAlmostEqual(
            r["parts"]["Tekne yakıtı"],
            boat,
            places=6
        )

        self.assertAlmostEqual(
            r["parts"]["Gübre (doğrudan N₂O)"],
            fertilizer,
            places=6
        )

        self.assertAlmostEqual(r["base"], 0)

        self.assertAlmostEqual(
            r["expanded"],
            boat + fertilizer,
            places=6
        )

        self.assertAlmostEqual(
            r["local_percent"],
            100,
            places=6
        )

    def test_04_reduction_scenario(self):
        d = empty_profile()

        d["electric_kwh"] = 1000
        d["car_fuel"] = "Benzin"
        d["car_liters"] = 100

        r = scenario(
            d,
            electricity=20,
            car=30,
            bags=0,
            heating=0
        )

        current = (
            1000 * 0.469
            + 100 * 2.075
        )

        alternative = (
            800 * 0.469
            + 70 * 2.075
        )

        difference = current - alternative
        percent = difference / current * 100

        self.assertAlmostEqual(
            r["current"],
            current,
            places=6
        )

        self.assertAlmostEqual(
            r["alternative"],
            alternative,
            places=6
        )

        self.assertAlmostEqual(
            r["difference"],
            difference,
            places=6
        )

        self.assertAlmostEqual(
            r["percent"],
            percent,
            places=6
        )

    def test_05_electricity_sensitivity(self):
        """Elektrik faktörünün +/- %10 duyarlılığı."""

        d = empty_profile()
        d["electric_kwh"] = 1000

        normal = calculate(d)["expanded"]

        factors_low = FACTORS.copy()
        factors_high = FACTORS.copy()

        factors_low["electric"] *= 0.90
        factors_high["electric"] *= 1.10

        low = calculate(
            d, factors_low
        )["expanded"]

        high = calculate(
            d, factors_high
        )["expanded"]

        self.assertAlmostEqual(
            normal, 469.0, places=6
        )

        self.assertAlmostEqual(
            low, 422.1, places=6
        )

        self.assertAlmostEqual(
            high, 515.9, places=6
        )

        self.assertAlmostEqual(
            (high - normal) / normal * 100,
            10,
            places=6
        )

        self.assertAlmostEqual(
            (low - normal) / normal * 100,
            -10,
            places=6
        )

        print("\nDUYARLILIK ANALIZI")
        print(
            f"Elektrik faktoru -%10: "
            f"{low:.2f} kg CO2e"
        )
        print(
            f"Referans faktor: "
            f"{normal:.2f} kg CO2e"
        )
        print(
            f"Elektrik faktoru +%10: "
            f"{high:.2f} kg CO2e"
        )

    def test_06_negative_consumption(self):
        d = empty_profile()
        d["electric_kwh"] = -100

        with self.assertRaises(ValueError):
            calculate(d)

    def test_07_invalid_reduction(self):
        d = empty_profile()

        with self.assertRaises(ValueError):
            scenario(d, electricity=110)

    def test_08_zero_reduction(self):
        d = empty_profile()
        d["electric_kwh"] = 1000

        r = scenario(
            d,
            electricity=0,
            car=0,
            bags=0,
            heating=0
        )

        self.assertAlmostEqual(
            r["current"],
            r["alternative"],
            places=6
        )

        self.assertAlmostEqual(
            r["difference"],
            0,
            places=6
        )

    def test_09_no_double_counting(self):
        d = empty_profile()

        d["electric_kwh"] = 1000
        d["wood_kg"] = 100

        r = calculate(d)

        self.assertAlmostEqual(
            r["expanded"],
            r["base"] + r["local"],
            places=6
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
