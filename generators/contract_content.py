# -*- coding: utf-8 -*-
"""
Mock contract content. Each entry is a list of (heading, body) sections.
heading=None means an unheaded paragraph (used deliberately to bury terms).
Prose is written to match ground_truth.json, with traps encoded on purpose.
"""

CONTRACTS = {

# ---------------------------------------------------------------- 01 CLEAN
"01_northwind_msa_CLEAN": {
    "title": "MASTER SUPPLY AGREEMENT",
    "sections": [
        (None, "This Master Supply Agreement (the \u201cAgreement\u201d) is entered into as of March 1, 2024 (the \u201cEffective Date\u201d) by and between Northwind Supply Co., a Delaware corporation (\u201cSupplier\u201d), and Keystone Procurement LLC (\u201cCustomer\u201d)."),
        ("1. Pricing", "Supplier shall provide the goods at the fixed unit prices set forth in this Agreement. Prices are firm for the duration of the Term and are not subject to increase."),
        ("2. Discounts", "Customer shall receive a two percent (2%) discount on all invoices."),
        ("3. Payment Terms", "Customer shall pay all undisputed invoices within thirty (30) days of the invoice date (Net 30)."),
        ("4. Minimum Commitment", "Customer commits to a minimum annual spend of $100,000 during each year of the Term."),
        ("5. Term", "The initial term of this Agreement is twenty-four (24) months from the Effective Date (the \u201cTerm\u201d)."),
        ("6. Renewal", "This Agreement shall automatically renew for successive twelve (12) month periods unless either party provides written notice of non-renewal at least sixty (60) days prior to the end of the then-current term."),
        ("7. Termination", "Either party may terminate this Agreement for convenience upon thirty (30) days prior written notice to the other party."),
        ("8. Limitation of Liability", "Each party\u2019s total aggregate liability under this Agreement shall not exceed $100,000."),
        ("9. Indemnification", "Each party shall indemnify and hold harmless the other party from third-party claims arising out of its own negligence or breach (mutual indemnification)."),
        ("10. Governing Law", "This Agreement shall be governed by the laws of the State of Delaware."),
    ],
},

# ------------------------------------------------------------- 02 MODERATE
"02_acme_msa_MODERATE": {
    "title": "MASTER SERVICES AND SUPPLY AGREEMENT",
    "sections": [
        (None, "This Master Services and Supply Agreement is made effective November 15, 2023, between Acme Industrial Partners, Inc. (\u201cVendor\u201d) and Keystone Procurement LLC (\u201cClient\u201d)."),
        ("1. Pricing Structure", "Pricing shall follow the tiered volume-based schedule attached hereto as Exhibit A, under which unit prices decrease as cumulative purchase volume increases across the defined tiers."),
        ("2. Prompt Payment Discount", "Provided that Client remits payment within ten (10) days of invoice, Client shall be entitled to a prompt-payment discount of five percent (5%) of the invoiced amount."),
        ("3. Invoicing and Payment", "Unless the prompt-payment discount is taken, Client shall remit payment in full no later than forty-five (45) days following the date of each invoice."),
        ("4. Volume Commitment", "Client commits to purchase a minimum committed volume equal to $250,000 per contract year."),
        ("5. Term of Agreement", "This Agreement shall remain in effect for an initial period of thirty-six (36) months."),
        ("6. Renewal of Term", "Upon expiry of the initial period the Agreement shall renew automatically for additional one-year periods, unless a party delivers written notice of its intent not to renew not fewer than ninety (90) days before the renewal date."),
        ("7. Termination", "This Agreement may be terminated by either party only in the event of a material breach that remains uncured for thirty (30) days after written notice. For the avoidance of doubt, neither party shall have the right to terminate this Agreement for convenience."),
        ("8. Limitation of Liability", "In no event shall Vendor\u2019s aggregate liability exceed Five Hundred Thousand Dollars ($500,000)."),
        ("9. Indemnification", "Vendor shall indemnify, defend, and hold harmless Client against any and all third-party claims arising from the goods or services provided hereunder. Client shall have no reciprocal indemnification obligation."),
        ("10. Governing Law", "This Agreement and any dispute arising hereunder shall be governed by and construed in accordance with the laws of the State of New York."),
    ],
},

# ------------------------------------------------------------- 03 MODERATE (SaaS)
"03_globex_saas_MODERATE": {
    "title": "CLOUD SERVICES SUBSCRIPTION AGREEMENT",
    "sections": [
        (None, "This Cloud Services Subscription Agreement (\u201cAgreement\u201d) is effective as of July 1, 2024 by and between Globex Cloud Systems (\u201cProvider\u201d) and Keystone Procurement LLC (\u201cSubscriber\u201d)."),
        ("1. Subscription and Fees", "Provider grants Subscriber a subscription to the platform for an annual subscription fee of $60,000, billed annually in advance. The subscription fee constitutes Subscriber\u2019s minimum annual commitment. Overage usage above the included quota is billed separately at the then-current rates."),
        ("2. Payment", "Subscriber shall pay each invoice within thirty (30) days of receipt."),
        ("3. Subscription Period", "The initial subscription period is twelve (12) months commencing on the Effective Date. The parties intend an ongoing relationship and, accordingly, this subscription will continue on a rolling annual basis renewing automatically at the end of each period unless Subscriber notifies Provider in writing at least thirty (30) days before the end of the current period, after which renewal shall not occur."),
        ("4. Termination", "Subscriber may terminate this Agreement for convenience at any time upon ninety (90) days written notice to Provider."),
        ("5. Limitation of Liability", "Provider\u2019s total liability arising out of or related to this Agreement shall not exceed the total fees paid by Subscriber in the twelve (12) months preceding the event giving rise to the claim."),
        ("6. Indemnification", "Each party shall indemnify the other against third-party claims to the extent caused by the indemnifying party\u2019s breach of this Agreement."),
        ("7. Governing Law", "This Agreement is governed by the laws of the State of California, without regard to its conflict of laws provisions."),
    ],
},

# ---------------------------------------------------------------- 04 MESSY
"04_initech_services_MESSY": {
    "title": "PROFESSIONAL SERVICES AGREEMENT",
    "sections": [
        (None, "THIS PROFESSIONAL SERVICES AGREEMENT, dated January 10, 2024, is by and between Initech Services Group (the \u201cContractor\u201d) and Keystone Procurement LLC (the \u201cCompany\u201d), and sets forth the terms under which Contractor will provide certain services."),
        ("1. Compensation", "Company shall compensate Contractor on a cost-plus basis, equal to Contractor\u2019s documented direct costs plus a fixed margin of fifteen percent (15%), invoiced monthly."),
        ("2. Payment", "Payment of each properly submitted invoice shall be due sixty (60) days after Company\u2019s receipt thereof."),
        ("3. Annual Minimum", "Company shall engage Contractor for services representing not less than $400,000 in fees during each twelve-month period of the engagement."),
        ("4. Term", "The term of this engagement shall be forty-eight (48) months from the date first written above, and shall not renew automatically; any continuation beyond the term requires a new written agreement executed by both parties."),
        ("5. Termination for Convenience", "Subject to Section 11, either party may terminate this Agreement for convenience upon one hundred twenty (120) days prior written notice."),
        ("6. Services", "Contractor shall perform the services described in each statement of work agreed by the parties from time to time."),
        (None, "The parties acknowledge that the services are integral to Company\u2019s operations and that continuity is essential during the initial ramp-up phase."),
        ("11. Restrictions on Termination", "Notwithstanding Section 5, the right to terminate for convenience shall not be exercisable during the first eighteen (18) months following the Effective Date, during which period this Agreement may be terminated only for material uncured breach."),
        ("12. Limitation of Liability", "The aggregate liability of either party under this Agreement shall in no circumstances exceed $150,000, regardless of the form of action."),
        ("13. Indemnity", "Company shall indemnify and hold harmless Contractor, its officers and employees, from and against any claims arising in connection with the engagement. No corresponding indemnity is provided by Contractor."),
        ("20. Miscellaneous", "Headings are for convenience only. This Agreement constitutes the entire agreement between the parties. The validity, interpretation, and performance of this Agreement shall be governed in all respects by the laws of the State of Texas. If any provision is held invalid, the remainder shall continue in effect."),
    ],
},

# ---------------------------------------------------------------- 05 MESSY
"05_umbrella_supply_MESSY": {
    "title": "SUPPLY AND DISTRIBUTION TERMS",
    "sections": [
        (None, "These Supply and Distribution Terms are agreed as of February 20, 2025 between Umbrella Supply Chain Ltd. and Keystone Procurement LLC, and the parties, intending to be legally bound, agree as follows in respect of the supply of consumable goods on an as-ordered basis whereby charges accrue according to actual quantities drawn down by the buyer during each monthly cycle and are reconciled at month end."),
        (None, "All amounts invoiced shall be payable upon receipt of the invoice, and a discount of ten percent (10%) shall be applied to the aggregate monthly charges where the buyer has maintained its standing order throughout the relevant month, it being understood that pricing is determined solely by usage and that no fixed periodic fee applies, and the buyer further undertakes that its drawn-down volume shall correspond to a minimum of $15,000 in each calendar month for the duration of the arrangement, failing which the supplier may adjust applicable unit rates."),
        (None, "This arrangement shall run for an initial period of twelve (12) months and shall thereafter continue automatically for further like periods unless either party gives forty-five (45) days written notice before the end of a period, and for the avoidance of doubt there is no right for either party to walk away from the arrangement for convenience during any period, termination being permitted only where the other party has committed a serious breach which it has failed to remedy."),
        (None, "Neither party shall be liable for indirect or consequential losses, and save as expressly stated nothing in these terms shall be taken to create any indemnity in favour of either party, each party bearing its own losses except to the extent prohibited by law."),
    ],
},

# ------------------------------------------------------------- 06 MODERATE
"06_stark_equipment_MODERATE": {
    "title": "EQUIPMENT SUPPLY AGREEMENT",
    "sections": [
        (None, "This Equipment Supply Agreement (\u201cAgreement\u201d) is entered into as of September 5, 2024 between Stark Equipment Co. (\u201cSupplier\u201d) and Keystone Procurement LLC (\u201cBuyer\u201d)."),
        ("1. Pricing", "Supplier shall charge a fixed monthly platform fee for base equipment access, plus usage-based charges for consumables drawn during the month. This hybrid pricing model applies throughout the Term."),
        ("2. Discounts", "Buyer shall receive a volume discount of eight percent (8%) on all consumable charges. In addition, Buyer may take a further two percent (2%) prompt-payment discount if any invoice is paid within fifteen (15) days."),
        ("3. Payment Terms", "Buyer shall pay all undisputed invoices within ninety (90) days of invoice date."),
        ("4. Minimum Spend", "There is no minimum spend or minimum purchase commitment under this Agreement."),
        ("5. Term", "The initial term is twelve (12) months. This Agreement does not renew automatically and will expire at the end of the initial term unless renewed by mutual written agreement."),
        ("6. Termination", "Buyer may terminate this Agreement for convenience upon thirty (30) days prior written notice. Supplier may terminate only for cause."),
        ("7. Limitation of Liability", "Supplier\u2019s aggregate liability under this Agreement shall not exceed Two Million Dollars ($2,000,000)."),
        ("8. Indemnification", "Each party shall indemnify and defend the other against third-party claims arising from its own acts or omissions (mutual)."),
        ("9. Governing Law", "This Agreement shall be governed by and construed under the laws of the State of Illinois."),
    ],
},

}
