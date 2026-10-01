# ─────────────────────────────────────────────────────────
# Part 3 · Training data — (query, label) tuples
# Three labels: search / extract / summarize
#
# ~20 examples per category. A bigger set (50-100 per class, generated once
# with an LLM) raises accuracy; ~20 is enough to demo a working classifier.
# ─────────────────────────────────────────────────────────

training_data: list[tuple[str, str]] = [
    # ── SEARCH — find / locate documents ─────────────────────────────
    ("find the invoices from march", "search"),
    ("search for the contracts with TechSoft", "search"),
    ("show the documents from 2024", "search"),
    ("where are the unpaid invoices", "search"),
    ("list the active contracts", "search"),
    ("find the invoice with number 1234", "search"),
    ("i want to see all receipts from april", "search"),
    ("identify the documents signed last month", "search"),
    ("show me the invoices from supplier ACME", "search"),
    ("find all expired contracts", "search"),
    ("search for documents containing the word penalty", "search"),
    ("which invoices do we have above 10000", "search"),
    ("locate the contract with TechCorp", "search"),
    ("display the invoices issued in Q1", "search"),
    ("i want the list of warehouse orders", "search"),
    ("search the archive for documents from 2023", "search"),
    ("find the annexes to the main contract", "search"),
    ("show the invoices due this week", "search"),
    ("where do i find the maintenance contract", "search"),
    ("list all documents for the client Popescu", "search"),

    # ── EXTRACT — pull structured data out of a document ─────────────
    ("extract the data from the invoice", "extract"),
    ("pull the amounts out of the contract", "extract"),
    ("parse the attached PDF", "extract"),
    ("extract the VAT id and the supplier address", "extract"),
    ("get the total value from this invoice", "extract"),
    ("extract the due date from the contract", "extract"),
    ("pull all line items from the invoice", "extract"),
    ("extract the names of the parties in the contract", "extract"),
    ("read the invoice number from the document", "extract"),
    ("extract the VAT from the attached invoice", "extract"),
    ("pull the contact details from the header", "extract"),
    ("parse the product table from the PDF", "extract"),
    ("extract the IBAN from the invoice", "extract"),
    ("get the payment terms from the contract", "extract"),
    ("extract the ordered quantities from the document", "extract"),
    ("pull the penalty clauses from the contract", "extract"),
    ("extract the validity period from the document", "extract"),
    ("read the net value and the gross value", "extract"),
    ("extract the registration number from the deed", "extract"),
    ("get the delivery address from the order", "extract"),

    # ── SUMMARIZE — condense / synthesize content ────────────────────
    ("summarize the monthly report", "summarize"),
    ("give me a summary of the contract", "summarize"),
    ("synthesize the 5 invoices", "summarize"),
    ("give me a short summary of the document", "summarize"),
    ("summarize the main clauses of the contract", "summarize"),
    ("give an overview of the march expenses", "summarize"),
    ("synthesize the conclusions of the report", "summarize"),
    ("i want a one-sentence summary of the invoice", "summarize"),
    ("briefly summarize the contract terms", "summarize"),
    ("write an executive summary of the annual report", "summarize"),
    ("condense the information from the 3 documents", "summarize"),
    ("summarize what the contract contains", "summarize"),
    ("give me the gist of the report in a few points", "summarize"),
    ("synthesize the differences between the two offers", "summarize"),
    ("summarize the Q1 activity", "summarize"),
    ("summarize the audit report", "summarize"),
    ("i want a synthesis of the invoices by supplier", "summarize"),
    ("briefly summarize the correspondence with the client", "summarize"),
    ("summarize the changes in the contract", "summarize"),
    ("synthesize the financial data from the report", "summarize"),
]
