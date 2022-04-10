from dataclasses import dataclass

@dataclass(frozen=True)
class Address:
    """
    Represents an address
    """
    city: str
    postal_code: str
    street: str
    number: str

    @staticmethod
    def from_xml(p):
        return Address(
            number=p.xpath("NumRue")[0].text,
            street=p.xpath("NomRue")[0].text,
            city=p.xpath("Ville")[0].text,
            postal_code=p.xpath("CodePostal")[0].text
        )

@dataclass(frozen=True)
class ElecInfo:
    """
    Represents the electrical grid status
    """
    status: str
    outage_start_date: str
    outage_end_date: str
    number_affected_homes: int
    grid_status: int
    title: str
    description: str
    outage: bool

    @staticmethod
    def from_json(coupure: dict, crise: dict):
        return ElecInfo(
            status=coupure["etatCoupure"],
            outage_start_date=coupure["dateCoupure"],
            outage_end_date=coupure["dateRealimentation"],
            number_affected_homes=coupure["nbFoyersCoupes"],
            grid_status=coupure["etatElectrique"],
            title=crise["titreCrise"],
            description=crise["messageLong"],
            outage=True
        )

    @staticmethod
    def no_outage():
        return ElecInfo(
            status="",
            outage_start_date="",
            outage_end_date="",
            number_affected_homes=0,
            grid_status=0,
            title="",
            description="",
            outage=False
        )
