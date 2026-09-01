from decimal import Decimal

# allow: SIZE_OK — compact sanitized SEC Company Facts fixture tables.


def valuation_payload() -> dict[str, object]:
    return {
        "company": "Test Co",
        "ticker": "TEST",
        "current_price": "20",
        "market_cap": "2000",
        "shares_outstanding": "100",
        "revenue": "460",
        "net_income": "200",
        "eps": "2",
        "free_cash_flow": "50",
        "cash": "90",
        "current_assets": "710",
        "current_liabilities": "200",
        "inventory": "50",
        "total_assets": "1000",
        "total_liabilities": "300",
        "total_debt": "50",
        "shareholder_equity": "400",
        "book_value_per_share": "4",
        "financial_currency": "USD",
        "market_currency": "USD",
        "provider": {"warnings": []},
        "missing_fields": [],
        "data_quality": {"currency_match": True},
        "fact_metadata": {
            "current_price": {"basis": "market_quote", "price_date": "2026-08-28"},
            "revenue": {"basis": "ttm", "period_end": "2026-06-30", "filed": "2026-07-31"},
            "net_income": {"basis": "ttm", "period_end": "2026-06-30", "filed": "2026-07-31"},
            "free_cash_flow": {"basis": "ttm"},
            "shareholder_equity": {"basis": "latest_snapshot", "period_end": "2026-06-30"},
            "shares_outstanding": {"basis": "latest_snapshot", "period_end": "2026-06-30"},
            "eps": {"basis": "ttm", "period_end": "2026-06-30"},
        },
    }


def companyfacts_payload() -> dict[str, object]:
    return {"facts": {"us-gaap": us_gaap_facts(), "dei": dei_facts()}}


def no_direct_eps_payload() -> dict[str, object]:
    payload = companyfacts_payload()
    del payload["facts"]["us-gaap"]["EarningsPerShareDiluted"]
    del payload["facts"]["us-gaap"]["EarningsPerShareBasic"]
    return payload


def wrong_unit_facts() -> dict[str, object]:
    return {
        "us-gaap": {
            "RevenueFromContractWithCustomerExcludingAssessedTax": {
                "units": {"shares": [row(9, "Q1")]}
            }
        }
    }


def stale_preferred_annual_facts() -> dict[str, object]:
    return {
        "us-gaap": {
            "RevenueFromContractWithCustomerExcludingAssessedTax": {
                "units": {"USD": [row(999, "FY", form="10-K", end="2022-01-31")]}
            },
            "SalesRevenueNet": {"units": {"USD": quarter_rows([100, 110, 120, 130])}},
        }
    }


def us_gaap_facts() -> dict[str, object]:
    return {
        "RevenueFromContractWithCustomerExcludingAssessedTax": {
            "units": {"USD": quarter_rows([100, 110, 120, 130])}
        },
        "Revenues": {"units": {"USD": [row(999, "Q4", end="2026-06-30")]}},
        "NetIncomeLoss": {"units": {"USD": quarter_rows([10, 11, 12, 13])}},
        "OperatingIncomeLoss": {"units": {"USD": quarter_rows([20, 22, 24, 26])}},
        "EarningsPerShareDiluted": {
            "units": {
                "USD/shares": quarter_rows([1, Decimal("1.1"), Decimal("1.2"), Decimal("1.3")])
            }
        },
        "EarningsPerShareBasic": {"units": {"USD/shares": quarter_rows([2, 2, 2, 2])}},
        "NetCashProvidedByUsedInOperatingActivities": {
            "units": {"USD": quarter_rows([15, 16, 17, 20])}
        },
        "PaymentsToAcquirePropertyPlantAndEquipment": {
            "units": {"USD": quarter_rows([-4, -5, -4, -5])}
        },
        "CashAndCashEquivalentsAtCarryingValue": {"units": {"USD": [row(90, "Q4", form="10-Q")]}},
        "AssetsCurrent": {
            "units": {
                "USD": [
                    row(700, "Q4", filed="2026-07-30"),
                    row(710, "Q4", form="10-Q/A", filed="2026-08-02"),
                ]
            }
        },
        "LiabilitiesCurrent": {"units": {"USD": [row(200, "Q4", form="10-Q")]}},
        "Assets": {"units": {"USD": [row(1000, "Q4", form="10-Q")]}},
        "Liabilities": {"units": {"USD": [row(300, "Q4", form="10-Q")]}},
        "LongTermDebtCurrent": {"units": {"USD": [snapshot_row(10, "Q4")]}},
        "LongTermDebtNoncurrent": {"units": {"USD": [snapshot_row(40, "Q4")]}},
        "StockholdersEquity": {"units": {"USD": [row(400, "Q4", form="10-Q")]}},
        "WeightedAverageNumberOfDilutedSharesOutstanding": {
            "units": {"shares": quarter_rows([100, 100, 100, 100])}
        },
        "WeightedAverageNumberOfSharesOutstandingBasic": {
            "units": {"shares": quarter_rows([98, 98, 98, 98])}
        },
    }


def dei_facts() -> dict[str, object]:
    return {
        "EntityCommonStockSharesOutstanding": {"units": {"shares": [row(100, "Q4", form="10-Q")]}}
    }


def quarter_rows(values: list[int | Decimal]) -> list[dict[str, object]]:
    fps = ("Q1", "Q2", "Q3", "Q4")
    starts = ("2025-07-01", "2025-10-01", "2026-01-01", "2026-04-01")
    ends = ("2025-09-30", "2025-12-31", "2026-03-31", "2026-06-30")
    return [
        row(value, fp, start=start, end=end)
        for value, fp, start, end in zip(values, fps, starts, ends, strict=True)
    ]


def row(
    value: int | Decimal,
    fp: str,
    *,
    form: str = "10-Q",
    filed: str = "2026-07-31",
    start: str = "2026-04-01",
    end: str = "2026-06-30",
) -> dict[str, object]:
    return {
        "val": value,
        "fy": 2026,
        "fp": fp,
        "form": form,
        "filed": filed,
        "end": end,
        "start": start,
        "frame": f"CY2026{fp}",
        "accn": f"accn-{fp}-{filed}",
    }


def snapshot_row(value: int | Decimal, fp: str, *, end: str = "2026-06-30") -> dict[str, object]:
    item = row(value, fp, end=end)
    del item["start"]
    return item


def apple_like_ytd_payload() -> dict[str, object]:
    return {
        "facts": {
            "us-gaap": {
                "RevenueFromContractWithCustomerExcludingAssessedTax": {
                    "units": {
                        "USD": [
                            fiscal_row(90, "Q4", "10-K", "2024-09-29", "2025-09-27", 2025),
                            fiscal_row(45, "Q3", "10-Q", "2024-09-29", "2025-06-28", 2025),
                            fiscal_row(21, "Q1", "10-Q", "2025-09-28", "2025-12-27", 2026),
                            fiscal_row(45, "Q2", "10-Q", "2025-09-28", "2026-03-28", 2026),
                            fiscal_row(72, "Q3", "10-Q", "2025-09-28", "2026-06-27", 2026),
                        ]
                    }
                },
                "NetIncomeLoss": {
                    "units": {
                        "USD": [
                            fiscal_row(18, "Q4", "10-K", "2024-09-29", "2025-09-27", 2025),
                            fiscal_row(9, "Q3", "10-Q", "2024-09-29", "2025-06-28", 2025),
                            fiscal_row(4, "Q1", "10-Q", "2025-09-28", "2025-12-27", 2026),
                            fiscal_row(9, "Q2", "10-Q", "2025-09-28", "2026-03-28", 2026),
                            fiscal_row(15, "Q3", "10-Q", "2025-09-28", "2026-06-27", 2026),
                        ]
                    }
                },
                "OperatingIncomeLoss": {
                    "units": {
                        "USD": [
                            fiscal_row(22, "Q4", "10-K", "2024-09-29", "2025-09-27", 2025),
                            fiscal_row(11, "Q3", "10-Q", "2024-09-29", "2025-06-28", 2025),
                            fiscal_row(5, "Q1", "10-Q", "2025-09-28", "2025-12-27", 2026),
                            fiscal_row(11, "Q2", "10-Q", "2025-09-28", "2026-03-28", 2026),
                            fiscal_row(18, "Q3", "10-Q", "2025-09-28", "2026-06-27", 2026),
                        ]
                    }
                },
                "EarningsPerShareDiluted": {
                    "units": {
                        "USD/shares": [
                            fiscal_row(8, "Q4", "10-K", "2024-09-29", "2025-09-27", 2025),
                            fiscal_row(6, "Q3", "10-Q", "2024-09-29", "2025-06-28", 2025),
                            fiscal_row(1, "Q1", "10-Q", "2025-09-28", "2025-12-27", 2026),
                            fiscal_row(3, "Q2", "10-Q", "2025-09-28", "2026-03-28", 2026),
                            fiscal_row(6, "Q3", "10-Q", "2025-09-28", "2026-06-27", 2026),
                        ]
                    }
                },
                "NetCashProvidedByUsedInOperatingActivities": {
                    "units": {
                        "USD": [
                            fiscal_row(25, "Q4", "10-K", "2024-09-29", "2025-09-27", 2025),
                            fiscal_row(12, "Q3", "10-Q", "2024-09-29", "2025-06-28", 2025),
                            fiscal_row(8, "Q1", "10-Q", "2025-09-28", "2025-12-27", 2026),
                            fiscal_row(18, "Q2", "10-Q", "2025-09-28", "2026-03-28", 2026),
                            fiscal_row(33, "Q3", "10-Q", "2025-09-28", "2026-06-27", 2026),
                        ]
                    }
                },
                "PaymentsToAcquirePropertyPlantAndEquipment": {
                    "units": {
                        "USD": [
                            fiscal_row(-7, "Q4", "10-K", "2024-09-29", "2025-09-27", 2025),
                            fiscal_row(-3, "Q3", "10-Q", "2024-09-29", "2025-06-28", 2025),
                            fiscal_row(-2, "Q1", "10-Q", "2025-09-28", "2025-12-27", 2026),
                            fiscal_row(-5, "Q2", "10-Q", "2025-09-28", "2026-03-28", 2026),
                            fiscal_row(-9, "Q3", "10-Q", "2025-09-28", "2026-06-27", 2026),
                        ]
                    }
                },
            },
            "dei": {},
        }
    }


def duplicate_annual_payload() -> dict[str, object]:
    return {
        "us-gaap": {
            "RevenueFromContractWithCustomerExcludingAssessedTax": {
                "units": {
                    "USD": [
                        fiscal_row(
                            80, "FY", "10-K", "2024-09-29", "2025-09-27", 2025, "2025-10-31"
                        ),
                        fiscal_row(
                            82, "FY", "10-K/A", "2024-09-29", "2025-09-27", 2025, "2025-11-15"
                        ),
                        fiscal_row(
                            70, "FY", "10-K", "2023-10-01", "2024-09-28", 2024, "2024-10-31"
                        ),
                    ]
                }
            }
        }
    }


def fiscal_row(
    value: int | Decimal,
    fp: str,
    form: str,
    start: str,
    end: str,
    fy: int,
    filed: str = "2026-07-31",
) -> dict[str, object]:
    return {
        "val": value,
        "fy": fy,
        "fp": fp,
        "form": form,
        "filed": filed,
        "end": end,
        "start": start,
        "frame": f"CY{end[:4]}{fp}",
        "accn": f"accn-{fy}-{fp}-{filed}",
    }
