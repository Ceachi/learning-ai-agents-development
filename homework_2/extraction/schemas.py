'''
Pydantic schemas for structured extraction (Lesson 3, §3).

BaseModel = single source of truth: type safety + validation + documentation.
Each Field(description=...) guides the LLM on WHAT to extract — the more precise
the description, the better the result. List[...] fields default to [] so a
missing list never fails validation.

Both Invoice and Contract expose a `numar` field, used as the JSON filename on
save (extraction/storage.py). Descriptions are in Romanian to match the source
documents in samples/.
'''

from pydantic import BaseModel, Field


class Product(BaseModel):
    '''Produs sau serviciu de pe o linie de factură.'''

    denumire: str = Field(description="Denumirea produsului sau serviciului")
    cantitate: float = Field(default=1, description="Cantitatea (numărul de unități)")
    pret_unitar: float = Field(default=0, description="Prețul unitar, fără TVA")
    total: float = Field(default=0, description="Valoarea liniei (cantitate × preț unitar)")


class Invoice(BaseModel):
    '''Schemă pentru extracția datelor dintr-o factură.'''

    numar: str = Field(description="Numărul facturii (ex: FV-2024-001)")
    data: str = Field(description="Data emiterii (format: YYYY-MM-DD sau cum apare în document)")
    furnizor: str = Field(default="", description="Numele furnizorului (cine emite factura)")
    client: str = Field(default="", description="Numele clientului (cine plătește)")
    produse: list[Product] = Field(
        default=[],
        description="Lista de produse/servicii facturate",
    )
    subtotal: float = Field(default=0, description="Subtotalul fără TVA, în RON")
    tva: float = Field(default=0, description="Valoarea TVA, în RON")
    total: float = Field(description="Suma totală de plată (cu TVA), în RON")


class Contract(BaseModel):
    '''Schemă pentru extracția datelor dintr-un contract.'''

    numar: str = Field(description="Numărul contractului (ex: CS-2024-015)")
    data_incheiere: str = Field(description="Data semnării/încheierii contractului")
    prestator: str = Field(default="", description="Numele prestatorului (cine furnizează serviciile)")
    beneficiar: str = Field(default="", description="Numele beneficiarului (cine primește serviciile)")
    valoare: float = Field(default=0, description="Valoarea totală a contractului, în moneda din document")
    durata_luni: int = Field(default=0, description="Durata contractului, în luni")
    obligatii_prestator: list[str] = Field(
        default=[],
        description="Lista obligațiilor asumate de prestator",
    )
