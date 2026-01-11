import pytz
from django.utils.translation import gettext_lazy as _
import uuid, base64


def jwt_payload_handler(user):
    """Custom payload handler
    Token encrypts the dictionary returned by this function, and can be
    decoded by rest_framework_jwt.utils.jwt_decode_handler
    """
    return {
        "id": user.pk,
        # 'name': user.name,
        "email": user.email,
        # "role": user.role,
        # "has_sales_access": user.has_sales_access,
        # "has_marketing_access": user.has_marketing_access,
        "file_prepend": user.file_prepend,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_active": user.is_active,
        # "is_admin": user.is_admin,
        "is_staff": user.is_staff,
        # "date_joined"
    }

def generate_code():
    code = str(uuid.uuid4()).replace('-', '').upper()[:12]
    return code

SEX = (
    ("Masculin", "Masculin"),
    ("Feminin","Feminin"),

)

TOGO_REGION = (
    ("Maritime","Maritime"),
    ("Plateaux","Plateaux"),
    ("Centrale", "Centrale"),
    ("Kara", "Kara"),
    ("Savane", "Savane"),

)

JOB_GRADES = (
 ('Intern','Intern'),
('Trainee','Trainee'),
('Associate','Associate'),
('Junior Analyst','Junior Analyst'),
('Junior Associate','Junior Associate'),
('Junior Engineer','Junior Engineer'),
('Analyst','Analyst'),
('Specialist','Specialist'),
('Coordinator','Coordinator'),
('Engineer','Engineer'),
('Supervisor','Supervisor'),
('Senior Analyst','Senior Analyst'),
('Senior Specialist','Senior Specialist'),
('Senior Engineer','Senior Engineer'),
('Manager','Manager'),
('Team Lead','Team Lead'),
('Lead Engineer','Lead Engineer'),
('Lead Developer','Lead Developer'),
('Project Lead','Project Lead'),
('Assistant Manager','Assistant Manager'),
('Senior Manager','Senior Manager'),
('Product Manager','Product Manager'),
('Director','Director'),
('Senior Director','Senior Director'),
('Associate Director','Associate Director'),
('Vice President (VP)','Vice President (VP)'),
('Senior Vice President (SVP)','Senior Vice President (SVP)'),
('Executive Vice President (EVP)','Executive Vice President (EVP)'),
('Chief Executive Officer (CEO)','Chief Executive Officer (CEO)'),
('Chief Financial Officer (CFO)','Chief Financial Officer (CFO)'),
('Chief Operations Officer (COO)','Chief Operations Officer (COO)'),
('Chief Technology Officer (CTO)','Chief Technology Officer (CTO)'),
('Chief Marketing Officer (CMO)','Chief Marketing Officer (CMO)'),
('Board Member','Board Member'),
('Chairman of the Board','Chairman of the Board'),
)

Departments = (
   ('Human Resources (HR)','Human Resources (HR)'),
('Finance & Accounting','Finance & Accounting'),
('Sales & Marketing','Sales & Marketing'),
('Operations','Operations'),
('Information Technology (IT)','Information Technology (IT)'),
('Research & Development (R&D)','Research & Development (R&D)'),
('Customer Service','Customer Service'),
('Product Management','Product Management'),
('Legal','Legal'),
('Supply Chain & Logistics','Supply Chain & Logistics'),
('Procurement','Procurement'),
('Engineering','Engineering'),
('Quality Assurance (QA)','Quality Assurance (QA)'),
('Administrative Services','Administrative Services'),
('Corporate Strategy & Planning','Corporate Strategy & Planning'),
('Public Relations (PR)','Public Relations (PR)'),
('Creative & Design','Creative & Design'),
('Facilities Management','Facilities Management'),
('Risk Management','Risk Management'),
('Training & Development','Training & Development'),
('Business Development','Business Development'),
('Compliance & Regulatory Affairs','Compliance & Regulatory Affairs'),
('Health, Safety, and Environment (HSE)','Health, Safety, and Environment (HSE)'),
('Internal Audit','Internal Audit'),
('Investor Relations','Investor Relations'),
)
TOGO_VILLE = (
    ("Grand Lome", "Grand Lome"),
    ("Baguida","Baguida"),
    ("Aneho", "Aneho"),
    ("Agoe", "Agoe"),
    ("Tsevie", "Tsevie"),
    ("Agbelouve", "Agbelouve"),
    ("Kpalime", "Kpalime"),
    ("Atapkame", "Atapkame"),
    ("Sotouboua", "Sotouboua"),
    ("Blitta", "Blitta"),
    ("Bafilo", "Bafilo"),
    ("Sokode", "Sokode"),
    ("Kara", "Kara"),
    ("Mango", "Mango"),
    ("Dapaong", "Dapaong"),
    ("Pya", "Pya"),
    ("Pya", "Pya"),

)

INDCHOICES = (
    ("ADVERTISING", "ADVERTISING"),
    ("AGRICULTURE", "AGRICULTURE"),
    ("APPAREL & ACCESSORIES", "APPAREL & ACCESSORIES"),
    ("AUTOMOTIVE", "AUTOMOTIVE"),
    ("BANKING", "BANKING"),
    ("BIOTECHNOLOGY", "BIOTECHNOLOGY"),
    ("BUILDING MATERIALS & EQUIPMENT", "BUILDING MATERIALS & EQUIPMENT"),
    ("CHEMICAL", "CHEMICAL"),
    ("COMPUTER", "COMPUTER"),
    ("EDUCATION", "EDUCATION"),
    ("ELECTRONICS", "ELECTRONICS"),
    ("ENERGY", "ENERGY"),
    ("ENTERTAINMENT & LEISURE", "ENTERTAINMENT & LEISURE"),
    ("FINANCE", "FINANCE"),
    ("FOOD & BEVERAGE", "FOOD & BEVERAGE"),
    ("GROCERY", "GROCERY"),
    ("HEALTHCARE", "HEALTHCARE"),
    ("INSURANCE", "INSURANCE"),
    ("LEGAL", "LEGAL"),
    ("MANUFACTURING", "MANUFACTURING"),
    ("PUBLISHING", "PUBLISHING"),
    ("REAL ESTATE", "REAL ESTATE"),
    ("SERVICE", "SERVICE"),
    ("SOFTWARE", "SOFTWARE"),
    ("SPORTS", "SPORTS"),
    ("TECHNOLOGY", "TECHNOLOGY"),
    ("TELECOMMUNICATIONS", "TELECOMMUNICATIONS"),
    ("TELEVISION", "TELEVISION"),
    ("TRANSPORTATION", "TRANSPORTATION"),
    ("VENTURE CAPITAL", "VENTURE CAPITAL"),
)



TYPECHOICES = (
    ("CUSTOMER", "CUSTOMER"),
    ("INVESTOR", "INVESTOR"),
    ("PARTNER", "PARTNER"),
    ("RESELLER", "RESELLER"),
)

CSAT = (
    ("0", 0),
    ("1", 1),
    ("2", 2),
    ("3", 3),
    ("4", 4),
    ("5", 5),
    ("6", 6),
    ("7", 7),
    ("8", 8),
    ("9", 9),
    ("10", 10),


)

ORG = (
    ("call center","Call Center"),
    ("FIN ","Finance"),
    ("CAO ","Administration Office"),
    ("news","News center"),

)
ROLES = (
    ("ADMIN", "ADMIN"),
    ("USER", "USER"),
)

LEAD_STATUS = (
    ("assigned", "Assigned"),
    ("in process", "In Process"),
    ("converted", "Converted"),
    ("recycled", "Recycled"),
    ("closed", "Closed"),
)


LEAD_SOURCE = (
    ("call", "Call"),
    ("email", "Email"),
    ("existing customer", "Existing Customer"),
    ("partner", "Partner"),
    ("public relations", "Public Relations"),
    ("compaign", "Campaign"),
    ("other", "Other"),
)

STATUS_CHOICE = (
    ("New", "New"),
    ("Assigned", "Assigned"),
    ("Pending", "Pending"),
    ("Closed", "Closed"),
    ("Rejected", "Rejected"),
    ("Duplicate", "Duplicate"),
)

PRIORITY_CHOICE = (
    ("Low", "Low"),
    ("Normal", "Normal"),
    ("High", "High"),
    ("Urgent", "Urgent"),
)

CASE_TYPE = (("Question", "Question"), ("Incident", "Incident"), ("Problem", "Problem"))

STAGES = (
    ("QUALIFICATION", "QUALIFICATION"),
    ("NEEDS ANALYSIS", "NEEDS ANALYSIS"),
    ("VALUE PROPOSITION", "VALUE PROPOSITION"),
    ("ID.DECISION MAKERS", "ID.DECISION MAKERS"),
    ("PERCEPTION ANALYSIS", "PERCEPTION ANALYSIS"),
    ("PROPOSAL/PRICE QUOTE", "PROPOSAL/PRICE QUOTE"),
    ("NEGOTIATION/REVIEW", "NEGOTIATION/REVIEW"),
    ("CLOSED WON", "CLOSED WON"),
    ("CLOSED LOST", "CLOSED LOST"),
)

SOURCES = (
    ("NONE", "NONE"),
    ("CALL", "CALL"),
    ("EMAIL", " EMAIL"),
    ("EXISTING CUSTOMER", "EXISTING CUSTOMER"),
    ("PARTNER", "PARTNER"),
    ("PUBLIC RELATIONS", "PUBLIC RELATIONS"),
    ("CAMPAIGN", "CAMPAIGN"),
    ("WEBSITE", "WEBSITE"),
    ("OTHER", "OTHER"),
)

EVENT_PARENT_TYPE = ((10, "Account"), (13, "Lead"), (14, "Opportunity"), (11, "Case"))

EVENT_STATUS = (
    ("Planned", "Planned"),
    ("Held", "Held"),
    ("Not Held", "Not Held"),
    ("Not Started", "Not Started"),
    ("Started", "Started"),
    ("Completed", "Completed"),
    ("Canceled", "Canceled"),
    ("Deferred", "Deferred"),
)


COUNTRIES = (
    ("GB", _("United Kingdom")),
    ("AF", _("Afghanistan")),
    ("AX", _("Aland Islands")),
    ("AL", _("Albania")),
    ("DZ", _("Algeria")),
    ("AS", _("American Samoa")),
    ("AD", _("Andorra")),
    ("AO", _("Angola")),
    ("AI", _("Anguilla")),
    ("AQ", _("Antarctica")),
    ("AG", _("Antigua and Barbuda")),
    ("AR", _("Argentina")),
    ("AM", _("Armenia")),
    ("AW", _("Aruba")),
    ("AU", _("Australia")),
    ("AT", _("Austria")),
    ("AZ", _("Azerbaijan")),
    ("BS", _("Bahamas")),
    ("BH", _("Bahrain")),
    ("BD", _("Bangladesh")),
    ("BB", _("Barbados")),
    ("BY", _("Belarus")),
    ("BE", _("Belgium")),
    ("BZ", _("Belize")),
    ("BJ", _("Benin")),
    ("BM", _("Bermuda")),
    ("BT", _("Bhutan")),
    ("BO", _("Bolivia")),
    ("BA", _("Bosnia and Herzegovina")),
    ("BW", _("Botswana")),
    ("BV", _("Bouvet Island")),
    ("BR", _("Brazil")),
    ("IO", _("British Indian Ocean Territory")),
    ("BN", _("Brunei Darussalam")),
    ("BG", _("Bulgaria")),
    ("BF", _("Burkina Faso")),
    ("BI", _("Burundi")),
    ("KH", _("Cambodia")),
    ("CM", _("Cameroon")),
    ("CA", _("Canada")),
    ("CV", _("Cape Verde")),
    ("KY", _("Cayman Islands")),
    ("CF", _("Central African Republic")),
    ("TD", _("Chad")),
    ("CL", _("Chile")),
    ("CN", _("China")),
    ("CX", _("Christmas Island")),
    ("CC", _("Cocos (Keeling) Islands")),
    ("CO", _("Colombia")),
    ("KM", _("Comoros")),
    ("CG", _("Congo")),
    ("CD", _("Congo, The Democratic Republic of the")),
    ("CK", _("Cook Islands")),
    ("CR", _("Costa Rica")),
    ("CI", _("Cote d'Ivoire")),
    ("HR", _("Croatia")),
    ("CU", _("Cuba")),
    ("CY", _("Cyprus")),
    ("CZ", _("Czech Republic")),
    ("DK", _("Denmark")),
    ("DJ", _("Djibouti")),
    ("DM", _("Dominica")),
    ("DO", _("Dominican Republic")),
    ("EC", _("Ecuador")),
    ("EG", _("Egypt")),
    ("SV", _("El Salvador")),
    ("GQ", _("Equatorial Guinea")),
    ("ER", _("Eritrea")),
    ("EE", _("Estonia")),
    ("ET", _("Ethiopia")),
    ("FK", _("Falkland Islands (Malvinas)")),
    ("FO", _("Faroe Islands")),
    ("FJ", _("Fiji")),
    ("FI", _("Finland")),
    ("FR", _("France")),
    ("GF", _("French Guiana")),
    ("PF", _("French Polynesia")),
    ("TF", _("French Southern Territories")),
    ("GA", _("Gabon")),
    ("GM", _("Gambia")),
    ("GE", _("Georgia")),
    ("DE", _("Germany")),
    ("GH", _("Ghana")),
    ("GI", _("Gibraltar")),
    ("GR", _("Greece")),
    ("GL", _("Greenland")),
    ("GD", _("Grenada")),
    ("GP", _("Guadeloupe")),
    ("GU", _("Guam")),
    ("GT", _("Guatemala")),
    ("GG", _("Guernsey")),
    ("GN", _("Guinea")),
    ("GW", _("Guinea-Bissau")),
    ("GY", _("Guyana")),
    ("HT", _("Haiti")),
    ("HM", _("Heard Island and McDonald Islands")),
    ("VA", _("Holy See (Vatican City State)")),
    ("HN", _("Honduras")),
    ("HK", _("Hong Kong")),
    ("HU", _("Hungary")),
    ("IS", _("Iceland")),
    ("IN", _("India")),
    ("ID", _("Indonesia")),
    ("IR", _("Iran, Islamic Republic of")),
    ("IQ", _("Iraq")),
    ("IE", _("Ireland")),
    ("IM", _("Isle of Man")),
    ("IL", _("Israel")),
    ("IT", _("Italy")),
    ("JM", _("Jamaica")),
    ("JP", _("Japan")),
    ("JE", _("Jersey")),
    ("JO", _("Jordan")),
    ("KZ", _("Kazakhstan")),
    ("KE", _("Kenya")),
    ("KI", _("Kiribati")),
    ("KP", _("Korea, Democratic People's Republic of")),
    ("KR", _("Korea, Republic of")),
    ("KW", _("Kuwait")),
    ("KG", _("Kyrgyzstan")),
    ("LA", _("Lao People's Democratic Republic")),
    ("LV", _("Latvia")),
    ("LB", _("Lebanon")),
    ("LS", _("Lesotho")),
    ("LR", _("Liberia")),
    ("LY", _("Libyan Arab Jamahiriya")),
    ("LI", _("Liechtenstein")),
    ("LT", _("Lithuania")),
    ("LU", _("Luxembourg")),
    ("MO", _("Macao")),
    ("MK", _("Macedonia, The Former Yugoslav Republic of")),
    ("MG", _("Madagascar")),
    ("MW", _("Malawi")),
    ("MY", _("Malaysia")),
    ("MV", _("Maldives")),
    ("ML", _("Mali")),
    ("MT", _("Malta")),
    ("MH", _("Marshall Islands")),
    ("MQ", _("Martinique")),
    ("MR", _("Mauritania")),
    ("MU", _("Mauritius")),
    ("YT", _("Mayotte")),
    ("MX", _("Mexico")),
    ("FM", _("Micronesia, Federated States of")),
    ("MD", _("Moldova")),
    ("MC", _("Monaco")),
    ("MN", _("Mongolia")),
    ("ME", _("Montenegro")),
    ("MS", _("Montserrat")),
    ("MA", _("Morocco")),
    ("MZ", _("Mozambique")),
    ("MM", _("Myanmar")),
    ("NA", _("Namibia")),
    ("NR", _("Nauru")),
    ("NP", _("Nepal")),
    ("NL", _("Netherlands")),
    ("AN", _("Netherlands Antilles")),
    ("NC", _("New Caledonia")),
    ("NZ", _("New Zealand")),
    ("NI", _("Nicaragua")),
    ("NE", _("Niger")),
    ("NG", _("Nigeria")),
    ("NU", _("Niue")),
    ("NF", _("Norfolk Island")),
    ("MP", _("Northern Mariana Islands")),
    ("NO", _("Norway")),
    ("OM", _("Oman")),
    ("PK", _("Pakistan")),
    ("PW", _("Palau")),
    ("PS", _("Palestinian Territory, Occupied")),
    ("PA", _("Panama")),
    ("PG", _("Papua New Guinea")),
    ("PY", _("Paraguay")),
    ("PE", _("Peru")),
    ("PH", _("Philippines")),
    ("PN", _("Pitcairn")),
    ("PL", _("Poland")),
    ("PT", _("Portugal")),
    ("PR", _("Puerto Rico")),
    ("QA", _("Qatar")),
    ("RE", _("Reunion")),
    ("RO", _("Romania")),
    ("RU", _("Russian Federation")),
    ("RW", _("Rwanda")),
    ("BL", _("Saint Barthelemy")),
    ("SH", _("Saint Helena")),
    ("KN", _("Saint Kitts and Nevis")),
    ("LC", _("Saint Lucia")),
    ("MF", _("Saint Martin")),
    ("PM", _("Saint Pierre and Miquelon")),
    ("VC", _("Saint Vincent and the Grenadines")),
    ("WS", _("Samoa")),
    ("SM", _("San Marino")),
    ("ST", _("Sao Tome and Principe")),
    ("SA", _("Saudi Arabia")),
    ("SN", _("Senegal")),
    ("RS", _("Serbia")),
    ("SC", _("Seychelles")),
    ("SL", _("Sierra Leone")),
    ("SG", _("Singapore")),
    ("SK", _("Slovakia")),
    ("SI", _("Slovenia")),
    ("SB", _("Solomon Islands")),
    ("SO", _("Somalia")),
    ("ZA", _("South Africa")),
    ("GS", _("South Georgia and the South Sandwich Islands")),
    ("ES", _("Spain")),
    ("LK", _("Sri Lanka")),
    ("SD", _("Sudan")),
    ("SR", _("Suriname")),
    ("SJ", _("Svalbard and Jan Mayen")),
    ("SZ", _("Swaziland")),
    ("SE", _("Sweden")),
    ("CH", _("Switzerland")),
    ("SY", _("Syrian Arab Republic")),
    ("TW", _("Taiwan, Province of China")),
    ("TJ", _("Tajikistan")),
    ("TZ", _("Tanzania, United Republic of")),
    ("TH", _("Thailand")),
    ("TL", _("Timor-Leste")),
    ("TG", _("Togo")),
    ("TK", _("Tokelau")),
    ("TO", _("Tonga")),
    ("TT", _("Trinidad and Tobago")),
    ("TN", _("Tunisia")),
    ("TR", _("Turkey")),
    ("TM", _("Turkmenistan")),
    ("TC", _("Turks and Caicos Islands")),
    ("TV", _("Tuvalu")),
    ("UG", _("Uganda")),
    ("UA", _("Ukraine")),
    ("AE", _("United Arab Emirates")),
    ("US", _("United States")),
    ("UM", _("United States Minor Outlying Islands")),
    ("UY", _("Uruguay")),
    ("UZ", _("Uzbekistan")),
    ("VU", _("Vanuatu")),
    ("VE", _("Venezuela")),
    ("VN", _("Viet Nam")),
    ("VG", _("Virgin Islands, British")),
    ("VI", _("Virgin Islands, U.S.")),
    ("WF", _("Wallis and Futuna")),
    ("EH", _("Western Sahara")),
    ("YE", _("Yemen")),
    ("ZM", _("Zambia")),
    ("ZW", _("Zimbabwe")),
)

CURRENCY_CODES = (
    ("AED", _("AED, Dirham")),
    ("AFN", _("AFN, Afghani")),
    ("ALL", _("ALL, Lek")),
    ("AMD", _("AMD, Dram")),
    ("ANG", _("ANG, Guilder")),
    ("AOA", _("AOA, Kwanza")),
    ("ARS", _("ARS, Peso")),
    ("AUD", _("AUD, Dollar")),
    ("AWG", _("AWG, Guilder")),
    ("AZN", _("AZN, Manat")),
    ("BAM", _("BAM, Marka")),
    ("BBD", _("BBD, Dollar")),
    ("BDT", _("BDT, Taka")),
    ("BGN", _("BGN, Lev")),
    ("BHD", _("BHD, Dinar")),
    ("BIF", _("BIF, Franc")),
    ("BMD", _("BMD, Dollar")),
    ("BND", _("BND, Dollar")),
    ("BOB", _("BOB, Boliviano")),
    ("BRL", _("BRL, Real")),
    ("BSD", _("BSD, Dollar")),
    ("BTN", _("BTN, Ngultrum")),
    ("BWP", _("BWP, Pula")),
    ("BYR", _("BYR, Ruble")),
    ("BZD", _("BZD, Dollar")),
    ("CAD", _("CAD, Dollar")),
    ("CDF", _("CDF, Franc")),
    ("CHF", _("CHF, Franc")),
    ("CLP", _("CLP, Peso")),
    ("CNY", _("CNY, Yuan Renminbi")),
    ("COP", _("COP, Peso")),
    ("CRC", _("CRC, Colon")),
    ("CUP", _("CUP, Peso")),
    ("CVE", _("CVE, Escudo")),
    ("CZK", _("CZK, Koruna")),
    ("DJF", _("DJF, Franc")),
    ("DKK", _("DKK, Krone")),
    ("DOP", _("DOP, Peso")),
    ("DZD", _("DZD, Dinar")),
    ("EGP", _("EGP, Pound")),
    ("ERN", _("ERN, Nakfa")),
    ("ETB", _("ETB, Birr")),
    ("EUR", _("EUR, Euro")),
    ("FJD", _("FJD, Dollar")),
    ("FKP", _("FKP, Pound")),
    ("GBP", _("GBP, Pound")),
    ("GEL", _("GEL, Lari")),
    ("GHS", _("GHS, Cedi")),
    ("GIP", _("GIP, Pound")),
    ("GMD", _("GMD, Dalasi")),
    ("GNF", _("GNF, Franc")),
    ("GTQ", _("GTQ, Quetzal")),
    ("GYD", _("GYD, Dollar")),
    ("HKD", _("HKD, Dollar")),
    ("HNL", _("HNL, Lempira")),
    ("HRK", _("HRK, Kuna")),
    ("HTG", _("HTG, Gourde")),
    ("HUF", _("HUF, Forint")),
    ("IDR", _("IDR, Rupiah")),
    ("ILS", _("ILS, Shekel")),
    ("INR", _("INR, Rupee")),
    ("IQD", _("IQD, Dinar")),
    ("IRR", _("IRR, Rial")),
    ("ISK", _("ISK, Krona")),
    ("JMD", _("JMD, Dollar")),
    ("JOD", _("JOD, Dinar")),
    ("JPY", _("JPY, Yen")),
    ("KES", _("KES, Shilling")),
    ("KGS", _("KGS, Som")),
    ("KHR", _("KHR, Riels")),
    ("KMF", _("KMF, Franc")),
    ("KPW", _("KPW, Won")),
    ("KRW", _("KRW, Won")),
    ("KWD", _("KWD, Dinar")),
    ("KYD", _("KYD, Dollar")),
    ("KZT", _("KZT, Tenge")),
    ("LAK", _("LAK, Kip")),
    ("LBP", _("LBP, Pound")),
    ("LKR", _("LKR, Rupee")),
    ("LRD", _("LRD, Dollar")),
    ("LSL", _("LSL, Loti")),
    ("LTL", _("LTL, Litas")),
    ("LVL", _("LVL, Lat")),
    ("LYD", _("LYD, Dinar")),
    ("MAD", _("MAD, Dirham")),
    ("MDL", _("MDL, Leu")),
    ("MGA", _("MGA, Ariary")),
    ("MKD", _("MKD, Denar")),
    ("MMK", _("MMK, Kyat")),
    ("MNT", _("MNT, Tugrik")),
    ("MOP", _("MOP, Pataca")),
    ("MRO", _("MRO, Ouguiya")),
    ("MUR", _("MUR, Rupee")),
    ("MVR", _("MVR, Rufiyaa")),
    ("MWK", _("MWK, Kwacha")),
    ("MXN", _("MXN, Peso")),
    ("MYR", _("MYR, Ringgit")),
    ("MZN", _("MZN, Metical")),
    ("NAD", _("NAD, Dollar")),
    ("NGN", _("NGN, Naira")),
    ("NIO", _("NIO, Cordoba")),
    ("NOK", _("NOK, Krone")),
    ("NPR", _("NPR, Rupee")),
    ("NZD", _("NZD, Dollar")),
    ("OMR", _("OMR, Rial")),
    ("PAB", _("PAB, Balboa")),
    ("PEN", _("PEN, Sol")),
    ("PGK", _("PGK, Kina")),
    ("PHP", _("PHP, Peso")),
    ("PKR", _("PKR, Rupee")),
    ("PLN", _("PLN, Zloty")),
    ("PYG", _("PYG, Guarani")),
    ("QAR", _("QAR, Rial")),
    ("RON", _("RON, Leu")),
    ("RSD", _("RSD, Dinar")),
    ("RUB", _("RUB, Ruble")),
    ("RWF", _("RWF, Franc")),
    ("SAR", _("SAR, Rial")),
    ("SBD", _("SBD, Dollar")),
    ("SCR", _("SCR, Rupee")),
    ("SDG", _("SDG, Pound")),
    ("SEK", _("SEK, Krona")),
    ("SGD", _("SGD, Dollar")),
    ("SHP", _("SHP, Pound")),
    ("SLL", _("SLL, Leone")),
    ("SOS", _("SOS, Shilling")),
    ("SRD", _("SRD, Dollar")),
    ("SSP", _("SSP, Pound")),
    ("STD", _("STD, Dobra")),
    ("SYP", _("SYP, Pound")),
    ("SZL", _("SZL, Lilangeni")),
    ("THB", _("THB, Baht")),
    ("TJS", _("TJS, Somoni")),
    ("TMT", _("TMT, Manat")),
    ("TND", _("TND, Dinar")),
    ("TOP", _("TOP, Paanga")),
    ("TRY", _("TRY, Lira")),
    ("TTD", _("TTD, Dollar")),
    ("TWD", _("TWD, Dollar")),
    ("TZS", _("TZS, Shilling")),
    ("UAH", _("UAH, Hryvnia")),
    ("UGX", _("UGX, Shilling")),
    ("USD", _("$, Dollar")),
    ("UYU", _("UYU, Peso")),
    ("UZS", _("UZS, Som")),
    ("VEF", _("VEF, Bolivar")),
    ("VND", _("VND, Dong")),
    ("VUV", _("VUV, Vatu")),
    ("WST", _("WST, Tala")),
    ("XAF", _("XAF, Franc")),
    ("XCD", _("XCD, Dollar")),
    ("XOF", _("XOF, Franc")),
    ("XPF", _("XPF, Franc")),
    ("YER", _("YER, Rial")),
    ("ZAR", _("ZAR, Rand")),
    ("ZMK", _("ZMK, Kwacha")),
    ("ZWL", _("ZWL, Dollar")),
)


def return_complete_address(self):
    address = ""
    if self.address_line:
        address += self.address_line
    if self.street:
        if address:
            address += ", " + self.street
        else:
            address += self.street
    if self.city:
        if address:
            address += ", " + self.city
        else:
            address += self.city
    if self.state:
        if address:
            address += ", " + self.state
        else:
            address += self.state
    if self.postcode:
        if address:
            address += ", " + self.postcode
        else:
            address += self.postcode
    if self.country:
        if address:
            address += ", " + self.get_country_display()
        else:
            address += self.get_country_display()
    return address


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


def convert_to_custom_timezone(custom_date, custom_timezone, to_utc=False):
    user_time_zone = pytz.timezone(custom_timezone)
    if to_utc:
        custom_date = user_time_zone.localize(custom_date.replace(tzinfo=None))
        user_time_zone = pytz.UTC
    return custom_date.astimezone(user_time_zone)


def append_str_to(append_to: str, *args, sep=", ", **kwargs):
    """Concatenate to a string.
    Args:
        append_to(str): The string to append to.
        args(list): list of string characters to concatenate.
        sep(str): Seperator to use between concatenated strings.
        kwargs(dict): Mapping of variables with intended string values.
    Returns:
        str, joined strings seperated
    """
    append_to = append_to or ""
    result_list = [append_to] + list(args) + list(kwargs.values())
    data = False
    for item in result_list:
        if item:
            data = True
            break
    return f"{sep}".join(filter(len, result_list)) if data else ""


TYPE_COMPANIES = (("Sole proprietorship", "Sole proprietorship"),
                  ("Partnership", "Partnership"),
                  ("Limited liability company (LLC)", "Limited liability company (LLC)"),
                  ("Corporation","Corporation"),
                  ("Cooperative", "Cooperative"),
                  ("Publicly traded company", "Publicly traded company"),
                  ("Privately held company", "Privately held company"),
                  ("Non-profit", "Non-profit"),

)

PARTENERSHIP_TYPE = (
    ("PARTENAIRE COMMERCIAL", "PARTENAIRE COMMERCIAL"),
    ("PARTENAIRE TECHNIQUE ", "PARTENAIRE TECHNIQUE "),
    ("PARTENAIRE FINANCIER ", "PARTENAIRE FINANCIER "),
    ("PARTENAIR MANAGEMENT ","PARTENAIR MANAGEMENT "),

)

PHONE_CODE = (
('+1','+1'),
('+7','+7'),
('+20','+20'),
('+27','+27'),
('+30','+30'),
('+31','+31'),
('+32','+32'),
('+33','+33'),
('+34','+34'),
('+36','+36'),
('+39','+39'),
('+40','+40'),
('+41','+41'),
('+43','+43'),
('+44','+44'),
('+45','+45'),
('+46','+46'),
('+47','+47'),
('+48','+48'),
('+49','+49'),
('+51','+51'),
('+52','+52'),
('+53','+53'),
('+54','+54'),
('+55','+55'),
('+56','+56'),
('+57','+57'),
('+58','+58'),
('+60','+60'),


('+61','+61'),
('+62','+62'),
('+63','+63'),
('+64','+64'),
('+64','+64'),
('+65','+65'),
('+66','+66'),
('+81','+81'),
('+82','+82'),
('+84','+84'),
('+86','+86'),
('+90','+90'),
('+91','+91'),
('+92','+92'),
('+93','+93'),
('+94','+94'),
('+95','+95'),
('+98','+98'),
('+211','+211'),
('+212','+212'),
('+212','+212'),
('+213','+213'),
('+216','+216'),
('+218','+218'),
('+220','+220'),
('+221','+221'),
('+222','+222'),
('+223','+223'),
('+224','+224'),
('+225','+225'),
('+226','+226'),
('+227','+227'),
('+228','+228'),
('+229','+229'),
('+230','+230'),
('+231','+231'),
('+232','+232'),
('+233','+233'),
('+234','+234'),
('+235','+235'),
('+236','+236'),
('+237','+237'),
('+238','+238'),
('+239','+239'),
('+240','+240'),
('+241','+241'),
('+242','+242'),
('+243','+243'),
('+244','+244'),
('+245','+245'),
('+246','+246'),
('+248','+248'),
('+249','+249'),
('+250','+250'),
('+251','+251'),
('+252','+252'),
('+253','+253'),
('+254','+254'),
('+255','+255'),
('+256','+256'),
('+257','+257'),
('+258','+258'),
('+260','+260'),
('+261','+261'),
('+262','+262'),
('+262','+262'),
('+263','+263'),
('+264','+264'),
('+265','+265'),
('+266','+266'),
('+267','+267'),
('+268','+268'),
('+269','+269'),
('+290','+290'),
('+291','+291'),
('+297','+297'),
('+298','+298'),
('+299','+299'),
('+350','+350'),
('+351','+351'),
('+352','+352'),
('+353','+353'),
('+354','+354'),
('+355','+355'),
('+356','+356'),
('+357','+357'),
('+358','+358'),
('+359','+359'),
('+370','+370'),
('+371','+371'),
('+372','+372'),
('+373','+373'),
('+374','+374'),
('+375','+375'),
('+376','+376'),
('+377','+377'),
('+378','+378'),
('+379','+379'),
('+380','+380'),
('+381','+381'),
('+382','+382'),
('+383','+383'),
('+385','+385'),
('+386','+386'),
('+387','+387'),
('+389','+389'),
('+420','+420'),
('+421','+421'),
('+423','+423'),
('+500','+500'),
('+501','+501'),
('+502','+502'),
('+503','+503'),
('+504','+504'),
('+505','+505'),
('+506','+506'),
('+507','+507'),
('+508','+508'),
('+509','+509'),
('+590','+590'),
('+590','+590'),
('+591','+591'),
('+592','+592'),
('+593','+593'),
('+595','+595'),
('+597','+597'),
('+598','+598'),
('+599','+599'),
('+599','+599'),
('+670','+670'),
('+672','+672'),
('+673','+673'),
('+674','+674'),
('+675','+675'),
('+676','+676'),
('+677','+677'),
('+678','+678'),
('+679','+679'),
('+680','+680'),
('+681','+681'),
('+682','+682'),
('+683','+683'),
('+685','+685'),
('+686','+686'),
('+687','+687'),
('+688','+688'),
('+689','+689'),
('+690','+690'),
('+691','+691'),
('+692','+692'),
('+850','+850'),
('+852','+852'),
('+853','+853'),
('+855','+855'),
('+856','+856'),
('+880','+880'),
('+886','+886'),
('+960','+960'),
('+961','+961'),
('+962','+962'),
('+963','+963'),
('+964','+964'),
('+965','+965'),
('+966','+966'),
('+967','+967'),
('+968','+968'),
('+970','+970'),
('+971','+971'),
('+972','+972'),
('+973','+973'),
('+974','+974'),
('+975','+975'),
('+976','+976'),
('+977','+977'),
('+992','+992'),
('+993','+993'),
('+994','+994'),
('+995','+995'),
('+996','+996'),
('+998','+998'),
('+1242','+1242'),
('+1246','+1246'),
('+1264','+1264'),
('+1268','+1268'),
('+1284','+1284'),
('+1340','+1340'),
('+1345','+1345'),
('+1441','+1441'),
('+1473','+1473'),
('+1649','+1649'),
('+1664','+1664'),
('+1670','+1670'),
('+1671','+1671'),
('+1684','+1684'),
('+1721','+1721'),
('+1758','+1758'),
('+1767','+1767'),
('+1784','+1784'),
('+1868','+1868'),
('+1869','+1869'),
('+1876','+1876'),
('+4779','+4779'),
('+441481','+441481'),
('+441534','+441534'),
('+441624','+441624'),
)

EMP_NUMBER = [('1','Less than 10 employees'),
              ('2','11 - 25 employees'), ('3', '26 - 50 employees'), ('4', '51 - 100 employees'),
          ('5', '101 - 250 employees '),('6','More than 250 employees')]

REVENUE = [('1','Less than 150 000 000'),
              ('2','150 000 000 -  500 000 000'), ('3', '500 000 001 - 1 000 000 000'),
          ('4', 'More 1 000 000 000 ')]

PARTNERSHIP_TYPE = (('PARTENAIRE COMMERCIAL', 'PARTENAIRE COMMERCIAL'),
                     ('PARTENAIRE TECHNIQUE', 'PARTENAIRE TECHNIQUE'),
                     ('PARTENAIRE FINANCIER', 'PARTENAIRE FINANCIER'),
                     ('PARTENAIR MANAGEMENT', 'PARTENAIR MANAGEMENT'))

FICHE_CAT = (('Agriculture', 'Agriculture'), ('Elevage', 'Elevage'), ('Pisciculture', 'Pisciculture'))

EXPERTISE_LEVEL = (('No Expertise needed', 'No Expertise Needed'),('Minimum Level', 'Minimum Level'),
                   ('Medium Level', 'Medium Level'), ('High Level', "high level")
                   )

JOB_TYPE = (("Full Time", "Full Time"), ("Part Time", "Part Time"), ("Intern", "Intern"))

BLOG_STATUS = (("DRAFT", "DRAFT"), ("PUBLISHED", "PUBLISHED"), ("ARCHIVED", "ARCHIVED"),)


OPPORTUNITY_TYPES = (

                    ('Offering Services','Offering Services'),
                    ('In Search of Service Provider','In Search of Service Provider'),

)

OPP_CAT = (('Services', 'Services'), ('Products','Products'))

REVIEWERS = (('Blessing','Blessing'), ('Babala','Bbala'))
APPROVERS = (('Hannah','Hannah'), ('Elizam','Elizam'))
PROJECT_DECISION = (('APPROVED', 'APPROVED'), ('REJECTED', 'REJECTED'),)

APPLICATION_STATUS_CHOICES = (
        ('Applied', 'Applied'),
        ('Under Review', 'Under Review'),
        ('Rejected', 'Rejected'),
        ('Hired', 'Hired')
    )

GENDER_CHOICES = [
    ('M', 'Male'),
    ('F', 'Female'),
    #('O', 'Other')
]

BLOOD_GROUPS = [
    ('O-', 'O-'),
    ('O+', 'O+'),
    ('A-', 'A-'),
    ('A+', 'A+'),
    ('B-', 'B-'),
    ('B+', 'B+'),
    ('AB-', 'AB-'),
    ('AB+', 'AB+'),
]


DEGREE_CHOICES = (
                ("Associate Degree - ASS", 'Associate Degree'),
                ("Bachelors Science - BS", 'Bachelors Science'),
                 ("Bachelors Arts - BA", 'Bachelors Arts'),
                 ("Master Business Administration - MBA", 'Master Business Administration'),
                 ("Masters - MS", 'Masters'),
                 ("High School - HS", 'High School'),
                  ("PhD", 'Doctorate'),
                  ("Certificate", "Certificate"),
)



SEX = (("F", "Female"), ("M", "Male"))
CONTRACT = (("DD", "Duree Determinee"), ("DI", "Duree Indeterminee"))


DEGREE_CHOICES = (("BS", 'Bachelors Science'),
                 ("BA", 'Bachelors Arts'),
                 ("MBA", 'Master Business Administration'),
                 ("M", 'Masters'),
                 ("HS", 'High School'),
                  ("PhD", 'Doctorate'),
                   ("CRT", 'Certificate'),
)

SEX = (("F", "Female"), ("M", "Male"))
CONTRACT = (("DD", "Duree Determinee"), ("DI", "Duree Indeterminee"))


DEPARTMENTS = (
     ('F', 'Finance'),
     ('S', 'Sales'),
     ('CC', 'Contact Center'),
     ('ACC', 'Accounting'),
     ('IT', 'Information Technology'),
     ('RM', 'Risk Management'),
)

EMP_TITLE = (
    ('OF', 'OFFICER'),
    ('MG', 'MANAGER'),
    ('SP', 'SUPERVISOR'),
    ('SG', 'SENIOR MG'),
    ('DT', 'DIRECTOR'),
    ('MD', 'MANAGING DIRECTOR'),
    ('CEO', 'CHIEF EXECUTIVE OFFICER'),

)

RATING_CHOICES = (
        (1, '1 star'),
        (2, '2 stars'),
        (3, '3 stars'),
        (4, '4 stars'),
        (5, '5 stars'),
    )
TRAININGS = [('TECHNOLOGY','TECHNOLOGY'),
             ('INFORMATION TECHNOLOGY','INFORMATION TECHNOLOGY'),
     ('FINANCE','FINANCE'), ('FINANCIAL MODELING', 'FINANCIAL MODELING'),
     ('DATA ANALYSIS', 'DATA ANALYSIS')
]

TRAININGS_DOMAIN = [('FINANCE','FINANCE')]
REQUIREMENTS = [
                ('BACHELORS','BACHELORS'),
                ('PROFESSIONALS','PROFESSIONALS'),
                ('ANYONE','ANYONE')
                ]

POSITIONS = [('OFFICER', 'OFFICER'), ('ASSISTANT VICE PRESIDENT', 'ASSISTANT VICE PRESIDENT'),
         ('VICE PRESIDENT', 'VICE PRESIDENT'), ('OTHER', 'OTHER')]

TRAINING_DAYS = [('MONDAY', 'MONDAY'),
                 ('TUESDAY', 'TUESDAY'),
                 ('WEDNESDAY', 'WEDNESDAY'),
                 ('THURSDAY', 'THURSDAY'),
                 ('FRIDAY', 'FRIDAY'),
                 ('SATURDAY', 'SATURDAY')
             ]

TRAININGS_DURATION = [("0:30 PER DAY","0:30 PER DAY"), ("0:45 PER DAY","0:45 PER DAY"),("1:00 PER DAY","1:00 PER DAY"),
                  ("1:30 PER DAY","1:30 PER DAY"), ("1:45 PER DAY","1:45 PER DAY"), ("2:00 PER DAY","2:00 PER DAY"),
              ("2:30 PER DAY","2:30 PER DAY"), ("2:45 PER DAY","2:45 PER DAY"), ("3:00 PER DAY","3:00 PER DAY")]

TRAININGS_MODE = [("ONLINE", "ONLINE"), ("IN PERSON", "IN PERSON"), ("HYBRID", "HYBRID")]

PROJECT_CATEGORY = [
    ("Industrial", "Industrial"),
    ("Agriculture","Agriculture"),
    ("Technology","Technology"),
    ("Fishing","Fishing"),
    ("Manufacturing", "Manufacturing"),
     ("Construction", "Construction"),
     ("Software Development", "Software Development"),
     ("Research", "Research"),
     ("Art and Design", "Art and Design"),
     ("Event Planning", "Event Planning"),
     ("Educational ", "Educational "),
     ("Community Development", "Community Development"),
     ("Business Development", "Business development"),
    ]


SERVICES_CATEGORIES = [
  ('Healthcare Services', 'Healthcare Services'),
('Educational Services:', 'Educational Services:'),
('Professional Consulting', 'Professional Consulting'),
('Financial Services', 'Financial Services'),
('Information Technology (IT) Services', 'Information Technology (IT) Services'),
('Real Estate Services', 'Real Estate Services'),
('Hospitality Services', 'Hospitality Services'),
('Transportation Services', 'Transportation Services'),
('Entertainment Services', 'Entertainment Services'),
('Marketing & Advertising Services:', 'Marketing & Advertising Services:'),
('Home Maintenance and Repair', 'Home Maintenance and Repair'),
('Beauty & Personal Care Services', 'Beauty & Personal Care Services'),
('Legal Services', 'Legal Services'),
('Creative Services', 'Creative Services'),
('Retail & E-commerce Services', 'Retail & E-commerce Services'),
('Environmental Services', 'Environmental Services'),
('Agricultural Services', 'Agricultural Services'),
('Human Resources (HR) & Recruitment', 'Human Resources (HR) & Recruitment'),
('Construction & Architecture', 'Construction & Architecture'),
('Security Services:', 'Security Services:')
]

PRODUCTS_CATEGORIES = [
    ('Electronics', 'Electronics'),
('Fashion & Apparel', 'Fashion & Apparel'),
('Home & Furniture', 'Home & Furniture'),
('Beauty & Personal Care', 'Beauty & Personal Care'),
('Automobiles & Vehicles', 'Automobiles & Vehicles'),
('Books & Stationery', 'Books & Stationery'),
('Food & Beverages', 'Food & Beverages'),
('Health & Wellness', 'Health & Wellness'),
('Toys & Games', 'Toys & Games'),
('Home Appliances', 'Home Appliances'),
('Sports & Outdoors:', 'Sports & Outdoors:'),
('Gardening & Landscaping', 'Gardening & Landscaping'),
('DIY & Home Improvement', 'DIY & Home Improvement'),
('Music & Entertainment', 'Music & Entertainment'),
('Pet Supplies & Products', 'Pet Supplies & Products'),
('Software & Apps', 'Software & Apps'),
('Industrial & B2B Products', 'Industrial & B2B Products'),
('Art & Crafts', 'Art & Crafts'),
('Travel & Leisure Products', 'Travel & Leisure Products'),
('Real Estate:', 'Real Estate:'),
('Agriculture Products','Agriculture Products')

]

PRODUCTS_OPPORTUNITIES = [
    ('Looking for a seller', 'Looking for a Seller'),
    ('Looking for a Buyer', 'Looking for a Buyer'),
]

MEASUREMENT_UNIT = [
    ('Unit', 'Unit'),
   ('Meter (m) - length','Meter (m) - length'),
('foot (ft) - length ','foot (ft) - length '),
('yard (yd) - length ','yard (yd) - length '),
('mile (mi) - length ','mile (mi) - length '),
('Inch (in) - length  ','Inch (in) - length  '),
('Kilogram (kg) - weight/mass','Kilogram (kg) - weight/mass'),
('Tonne (t) - weight/mass','Tonne (t) - weight/mass'),
('Pound (lb) - weight/mass','Pound (lb) - weight/mass'),
('ounce (oz) - weight/mass','ounce (oz) - weight/mass'),
('ounce (oz) - volume ','ounce (oz) - volume '),
('Square inches (in²) - area','Square inches (in²) - area'),
('Square meter (m²) - area','Square meter (m²) - area'),
('hectares - area','hectares - area'),
('acres - area','acres - area'),
('square feet (ft²) - area','square feet (ft²) - area'),
('Gallon (gal) - volume ','Gallon (gal) - volume '),
('Liter (L) - volume','Liter (L) - volume'),
('pint (pt) - volume ','pint (pt) - volume '),
]

CURRENCIES_SYMBOLS = [
    ('Dinar', 'د.ج'),
('Kwanza', 'Kz'),
('Pula', 'P'),
('CFA Franc', 'CFA'),
('Franc', 'FBu'),
('Escudo', 'Esc$'),
('Franc', 'CF'),
('Franc', 'FC'),
('Franc', 'Fdj'),
('Pound', 'E£'),
('Nakfa', 'Nfk'),
('Lilangeni', 'L'),
('Birr', 'Br'),
('Dalasi', 'D'),
('Cedi', '₵'),
('Franc', 'GNF'),
('Shilling', 'KSh'),
('Loti', 'L'),
('Dollar', 'L$'),
('Dinar', 'ل.د'),
('Ariary', 'Ar'),
('Kwacha', 'MK'),
('Ouguiya', 'UM'),
('Rupee', '₨'),
('Dirham', 'د.م.'),
('Metical', 'MT'),
('Dollar', 'N$'),
('Naira', '₦'),
('Franc', 'FRw'),
('Dobra', 'Db'),
('Leone', 'Le'),
('Shilling', 'SOS'),
('Rand', 'R'),
('Pound', 'SSP'),
('Pound', 'SDG'),
('Shilling', 'TSh'),
('Dinar', 'د.ت'),
('Shilling', 'USh'),
('Kwacha', 'ZK'),
('Dollar', 'Z$'),
('SGD', 'S$'),
('USD', '$'),
('Rand', 'R'),
('Pound', 'E£'),
('Euro', '€'),
('Real', 'R$'),
('Yuan', '¥'),
('Pound Sterling', '£'),
('Ruble', '₽'),
('Dollar', 'C$'),

]

DISCOUNTS = [
    ('5%','5%'),
    ('10%','10%'),
    ('15%','15%'),
    ('20%','20%'),

]

# utils.py in one of your apps

from django.core.mail import send_mail
from django.conf import settings

def send_notification_email(subject, message, recipient_list):
    send_mail(
        subject,
        message,
        settings.EMAIL_HOST_USER,
        recipient_list,
        fail_silently=False,
    )

###Then, modify your send_notification_email function to use this template.
###<!-- templates/email_template.html -->

##<!html>
## <body>
##<h1>{{ subject }}</h1>
##<p>{{ message }}</p>
##</body>
##</html>

from django.core.mail import EmailMessage
from django.template.loader import render_to_string

def send_notification_email(subject, message, recipient_list):
    context = {'subject': subject, 'message': message}
    email_content = render_to_string('/blogs/email_template.html', context)

    email = EmailMessage(
        subject,
        email_content,
        settings.EMAIL_HOST_USER,
        recipient_list
    )
    email.content_subtype = "html"  # Set the content type to HTML
    email.send()


STATES = (
   ('AL',  'Alabama'),
('AK',  'Alaska'),
('AZ',  'Arizona'),
('AR',  'Arkansas'),
('CA',  'California'),
('CO',  'Colorado'),
('CT',  'Connecticut'),
('DE',  'Delaware'),
('FL',  'Florida'),
('GA',  'Georgia'),
('HI',  'Hawaii'),
('ID',  'Idaho'),
('IL',  'Illinois'),
('IN',  'Indiana'),
('IA',  'Iowa'),
('KS',  'Kansas'),
('KY',  'Kentucky'),
('LA',  'Louisiana'),
('ME',  'Maine'),
('MD',  'Maryland'),
('MA',  'Massachusetts'),
('MI',  'Michigan'),
('MN',  'Minnesota'),
('MS',  'Mississippi'),
('MO',  'Missouri'),
('MT',  'Montana'),
('NE',  'Nebraska'),
('NV',  'Nevada'),
('NH',  'New Hampshire'),
('NJ',  'New Jersey'),
('NM',  'New Mexico'),
('NY',  'New York'),
('NC',  'North Carolina'),
('ND',  'North Dakota'),
('OH',  'Ohio'),
('OK',  'Oklahoma'),
('OR',  'Oregon'),
('PA',  'Pennsylvania'),
('RI',  'Rhode Island'),
('SC',  'South Carolina'),
('SD',  'South Dakota'),
('TN',  'Tennessee'),
('TX',  'Texas'),
('UT',  'Utah'),
('VT',  'Vermont'),
('VA',  'Virginia'),
('WA',  'Washington'),
('WV',  'West Virginia'),
('WI',  'Wisconsin'),
('WY',  'Wyoming'),
    )


MEMBERSHIP_TYPE = [
                    ("EXPERT", "EXPERT"),
                     ("COMPANY", "COMPANY"),
                     ("PARTNER COMPANY", "PARTNER COMPANY"),
                     ("ASSOCIATIONS & FEDERATORS", "ASSOCIATIONS & FEDERATORS"),
                      ("LOCAL COMMUNITY", "LOCAL COMMUNITY"),
                       ("STATE AGENCIY", "STATE AGENCY"),
]

PROJECT_NEEDS = [
    ("TECHNICAL", "TECHNICAL"),
    ("FINANCING", "FINANCING"),
    ("MANAGERIAL", "MANAGERIAL"),
    ("COMMERCIAL", "COMMERCIAL"),

]


DOMAIN_EXPERTISE = [
    
 ('Human Resources and Talent Management','Human Resources and Talent Management'),
('Finance and Accounting','Finance and Accounting'),
('Marketing and Communications','Marketing and Communications'),
('Sales and Business Development','Sales and Business Development'),
('Technology and IT','Technology and IT'),
('Operations and Supply Chain Management','Operations and Supply Chain Management'),
('Legal and Compliance','Legal and Compliance'),
('Healthcare and Medical','Healthcare and Medical'),
('Education and Training','Education and Training'),
('Engineering and Technical Fields','Engineering and Technical Fields'),
('Manufacturing and Production','Manufacturing and Production'),
('Customer Service and Support','Customer Service and Support'),
('Research and Development (R&D)','Research and Development (R&D)'),
('Creative and Design','Creative and Design'),
('Project Management','Project Management'),
('Energy and Environmental Sustainability','Energy and Environmental Sustainability'),
('Real Estate and Construction','Real Estate and Construction'),
('Agriculture and Food Industry','Agriculture and Food Industry'),
('Media and Entertainment','Media and Entertainment'),
('Sales and Retail Management','Sales and Retail Management'),
('Transportation and Logistics','Transportation and Logistics'),
('Hospitality and Tourism','Hospitality and Tourism'),
('Sports and Recreation','Sports and Recreation'),
('Arts and Culture','Arts and Culture')   
]

import pdfkit
from django.template.loader import render_to_string
from django.conf import settings
import os

def generate_analysis_pdf(context):
    """Generate PDF from analysis data"""
    # Render the template to string
    html_string = render_to_string('data_analytics/pdf_template.html', context)
    
    # PDF options
    options = {
        'page-size': 'A4',
        'margin-top': '0.75in',
        'margin-right': '0.75in',
        'margin-bottom': '0.75in',
        'margin-left': '0.75in',
        'encoding': "UTF-8",
        'no-outline': None,
        'enable-local-file-access': None
    }
    
    # Create PDF
    pdf = pdfkit.from_string(html_string, False, options=options)
    
    return pdf

from django.core.cache import cache
from django.conf import settings
import hashlib
import json

class AnalysisCache:
    @staticmethod
    def get_cache_key(pk, context_data):
        """Generate a unique cache key based on data and parameters"""
        # Create a hash of the context data to detect changes
        context_hash = hashlib.md5(
            json.dumps(context_data, sort_keys=True).encode('utf-8')
        ).hexdigest()
        return f'analysis_pdf_{pk}_{context_hash}'

    @staticmethod
    def get_cached_pdf(pk, context_data):
        """Get cached PDF if it exists"""
        cache_key = AnalysisCache.get_cache_key(pk, context_data)
        return cache.get(cache_key)

    @staticmethod
    def cache_pdf(pk, context_data, pdf_content, timeout=3600):  # Cache for 1 hour
        """Cache the generated PDF"""
        cache_key = AnalysisCache.get_cache_key(pk, context_data)
        cache.set(cache_key, pdf_content, timeout)

import os
from PyPDF2 import PdfFileWriter, PdfFileReader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.files.base import ContentFile
import fitz  # PyMuPDF
import math

class ProtectedFileStorage1(FileSystemStorage):
    def __init__(self):
        super().__init__(location=settings.PROTECTED_MEDIA_ROOT)
        
    def _save(self, name, content):
        if name.lower().endswith('.pdf'):
            return self._save_protected_pdf(name, content)
        return super()._save(name, content)
    
    def _save_protected_pdf(self, name, content):
        # Create temporary file
        temp_path = super()._save(f"temp_{name}", content)
        
        try:
            # Open the PDF
            pdf_document = fitz.open(os.path.join(self.location, temp_path))
            
            # Add watermark to each page
            for page in pdf_document:
                # Get page dimensions
                rect = page.rect
                
                # Create watermark text
                watermark_text = "CONFIDENTIAL - DO NOT DISTRIBUTE"
                font_size = 20  # Increased for better visibility
                
                red_color = (1, 0, 0)  # Red c 
                # Calculate center position
                center_x = rect.width / 5
                center_y = rect.height / 2
                
                # Add text watermark multiple times for darker effect
                for i in range(3):  # Adding text 3 times to make it more visible
                    page.insert_text(
                        point=(center_x, center_y),  # position
                        text=watermark_text,
                        fontsize=font_size,
                        color= red_color,  # gray color
                    )
            
            # Save with security
            pdf_document.save(
                os.path.join(self.location, name),
                encryption=fitz.PDF_ENCRYPT_AES_256,  # Strong encryption
                owner_pw="123password",  # Set owner password
                user_pw="123password",    # Set user password
                permissions=fitz.PDF_PERM_PRINT  # Only allow printing
            )
            
            # Clean up
            pdf_document.close()
            
        finally:
            # Always clean up the temporary file
            if os.path.exists(os.path.join(self.location, temp_path)):
                os.remove(os.path.join(self.location, temp_path))
        
        return name

class ProtectedFileStorage(FileSystemStorage):
    def __init__(self):
        super().__init__(location=settings.MEDIA_ROOT)
        
    def _save(self, name, content):
        if name.lower().endswith('.pdf'):
            return self._save_watermarked_pdf(name, content)
        return super()._save(name, content)
    
    def _save_watermarked_pdf(self, name, content):
        temp_path = super()._save(f"temp_{name}", content)
        
        try:
            pdf_document = fitz.open(os.path.join(self.location, temp_path))
            
            for page in pdf_document:
                rect = page.rect
                width = rect.width
                height = rect.height
                
                watermark_text = "CONFIDENTIAL - DO NOT DISTRIBUTE"
                font_size = 20
                
                for i in range(0, int(height), 200):
                    for j in range(0, int(width), 300):
                        page.insert_text(
                            point=(j, i),
                            text=watermark_text,
                            fontsize=font_size
                            #rotate=45
                        )
            
            pdf_document.save(
                os.path.join(self.location, name)
            )
            
            pdf_document.close()
            
        finally:
            if os.path.exists(os.path.join(self.location, temp_path)):
                os.remove(os.path.join(self.location, temp_path))
        
        return name

''' 
from core.models import Messaging, MessageAttachment, MessageNotification

def create_message(sender, receiver, conversation, content, subject=None, category=None, files=None):
    """
    Centralized function to create messages consistently across the application
    """
    # Create message
    message = Messaging(
        conversation=conversation,
        message_sender=sender,
        sender_email=sender.email,
        message_receiver=receiver,
        subject=subject or conversation.subject,
        content=content
    )
    
    # Set category if provided
    if category:
        message.category = category
        
    # Save the message
    message.save()
    
    # Handle file attachments
    if files:
        for f in files:
            try:
                attachment = MessageAttachment(
                    messaging=message,
                    file=f,
                    file_name=f.name,
                    file_size=f.size,
                    file_type=f.content_type
                )
                attachment.save()
            except Exception as e:
                print(f"Error saving attachment: {e}")
    
    # Create notification
    try:
        MessageNotification.objects.create(
            user=receiver,
            messaging=message
        )
    except Exception as e:
        print(f"Error creating notification: {e}")
        
    return message
    '''
    
# Constants for choices
ASSISTANCE_TYPE = [
    ('UNDERSTANDING', _('Understanding the technical sheet')),
    ('IMPLEMENTATION', _('Help implementing the techniques')),
    ('ADAPTATION', _('Adapting techniques to my specific conditions')),
    ('EQUIPMENT', _('Equipment and supplies guidance')),
    ('MARKETING', _('Marketing and sales assistance')),
    ('INDUSTRIALIZATION', _('Scaling up to industrial level')),
    ('EXPORT', _('Import/Export opportunities')),
    ('OTHER', _('Other assistance')),
]

FARM_SIZE_CHOICES = [
    ('SMALL', _('Small-scale farm (less than 5 hectares)')),
    ('MEDIUM', _('Medium-scale farm (5-20 hectares)')),
    ('LARGE', _('Large-scale farm (more than 20 hectares)')),
    ('INDUSTRIAL', _('Industrial operation')),
    ('BACKYARD', _('Backyard/Home garden')),
]

EXPERIENCE_LEVEL = [
    ('BEGINNER', _('Beginner')),
    ('INTERMEDIATE', _('Intermediate')),
    ('ADVANCED', _('Advanced')),
    ('EXPERT', _('Expert')),
]

URGENCY_LEVEL = [
    ('LOW', _('Low - Planning for future season')),
    ('MEDIUM', _('Medium - Need help within a month')),
    ('HIGH', _('High - Current season issue')),
    ('URGENT', _('Urgent - Immediate assistance needed')),
]

STATUS_CHOICES = [
    ('PENDING', _('Pending')),
    ('REVIEWING', _('Under Review')),
    ('ASSIGNED', _('Assigned')),
    ('IN_PROGRESS', _('In Progress')),
    ('COMPLETED', _('Completed')),
    ('CLOSED', _('Closed')),
]
###### Data Science Utilities Functions ######
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
import plotly.utils
import io
import base64
import json
import os
from datetime import datetime
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
import warnings
warnings.filterwarnings('ignore')

# Try to import PyCaret with version detection
try:
    import pycaret
    PYCARET_VERSION = pycaret.__version__
    print(f"PyCaret version: {PYCARET_VERSION}")
    
    # Import based on version
    try:
        # For PyCaret 3.x
        from pycaret.regression import RegressionExperiment
        from pycaret.classification import ClassificationExperiment
        from pycaret.clustering import ClusteringExperiment
        PYCARET_V3 = True
        print("Using PyCaret 3.x API")
    except ImportError:
        # For PyCaret 2.x
        from pycaret.regression import setup as reg_setup, compare_models as reg_compare, finalize_model as reg_finalize, pull as reg_pull
        from pycaret.classification import setup as clf_setup, compare_models as clf_compare, finalize_model as clf_finalize, pull as clf_pull
        from pycaret.clustering import setup as clust_setup, create_model as clust_create, pull as clust_pull
        PYCARET_V3 = False
        print("Using PyCaret 2.x API")
    
    PYCARET_AVAILABLE = True
except ImportError as e:
    PYCARET_AVAILABLE = False
    PYCARET_V3 = False
    print(f"PyCaret not available: {e}")
    print("Install with: pip install pycaret")

def get_pycaret_setup_params():
    """Get appropriate setup parameters based on PyCaret version"""
    if not PYCARET_AVAILABLE:
        return {}
    
    # Common parameters
    base_params = {
        'session_id': 123,
        'train_size': 0.8,
        'use_gpu': False,
    }
    
    # Version-specific parameters
    if PYCARET_V3:
        # PyCaret 3.x parameters
        version_params = {
            'verbose': False,  # Replaces 'silent'
            'system_log': False,
        }
    else:
        # PyCaret 2.x parameters
        version_params = {
            'silent': True,  # Only for 2.x
            'verbose': False,
        }
    
    return {**base_params, **version_params}

def run_ml_experiment(experiment):
    """Run machine learning experiment using PyCaret with version compatibility"""
    if not PYCARET_AVAILABLE:
        raise Exception("PyCaret is not available. Please install it using: pip install pycaret")
    
    try:
        # Read dataset
        df = read_dataset(experiment.dataset.file.path)
        
        # Update experiment status
        experiment.status = 'running'
        experiment.save()
        
        # Prepare data based on experiment type
        results = {}
        
        if experiment.ml_type == 'regression':
            results = run_regression_experiment_v2(df, experiment)
        elif experiment.ml_type == 'classification':
            results = run_classification_experiment_v2(df, experiment)
        elif experiment.ml_type == 'clustering':
            results = run_clustering_experiment_v2(df, experiment)
        else:
            raise Exception(f"ML type {experiment.ml_type} not supported yet")
        
        return results
        
    except Exception as e:
        experiment.status = 'failed'
        experiment.error_message = str(e)
        experiment.save()
        raise Exception(f"Error running ML experiment: {str(e)}")

def run_regression_experiment_v2(df, experiment):
    """Run regression experiment with version compatibility"""
    try:
        target = experiment.target_variable
        features = experiment.features
        
        # Prepare data
        ml_df = df[features + [target]].copy()
        ml_df = ml_df.dropna()
        
        if len(ml_df) == 0:
            raise Exception("No data available after removing missing values")
        
        # Get setup parameters
        setup_params = get_pycaret_setup_params()
        
        if PYCARET_V3:
            # PyCaret 3.x approach
            reg_exp = RegressionExperiment()
            reg_exp.setup(
                data=ml_df,
                target=target,
                **setup_params
            )
            
            # Compare models
            best_models = reg_exp.compare_models(
                include=['lr', 'rf', 'gbr', 'dt', 'ridge'],
                sort='RMSE',
                n_select=5,
                verbose=False
            )
            
            # Get results
            results_df = reg_exp.pull()
            
            # Finalize best model
            if isinstance(best_models, list):
                best_model = reg_exp.finalize_model(best_models[0])
            else:
                best_model = reg_exp.finalize_model(best_models)
            
        else:
            # PyCaret 2.x approach
            reg_setup(
                data=ml_df,
                target=target,
                **setup_params
            )
            
            # Compare models
            best_models = reg_compare(
                include=['lr', 'rf', 'gbr', 'dt', 'ridge'],
                sort='RMSE',
                n_select=5
            )
            
            # Get results
            results_df = reg_pull()
            
            # Finalize best model
            best_model = reg_finalize(best_models.iloc[0] if hasattr(best_models, 'iloc') else best_models)
        
        # Process results
        model_comparison = results_df.to_dict('records') if hasattr(results_df, 'to_dict') else []
        best_model_name = str(type(best_model).__name__)
        
        # Get best score
        if len(model_comparison) > 0:
            best_score = float(model_comparison[0].get('RMSE', 0))
        else:
            best_score = 0.0
        
        # Feature importance
        feature_importance = get_feature_importance(best_model, features)
        
        return {
            'best_model': best_model_name,
            'best_score': best_score,
            'model_results': {
                'rmse': best_score,
                'r2': float(model_comparison[0].get('R2', 0)) if model_comparison else 0,
                'mae': float(model_comparison[0].get('MAE', 0)) if model_comparison else 0,
                'model_type': 'regression'
            },
            'model_comparison': model_comparison[:5],
            'feature_importance': feature_importance
        }
        
    except Exception as e:
        raise Exception(f"Error in regression experiment: {str(e)}")

def run_classification_experiment_v2(df, experiment):
    """Run classification experiment with version compatibility"""
    try:
        target = experiment.target_variable
        features = experiment.features
        
        # Prepare data
        ml_df = df[features + [target]].copy()
        ml_df = ml_df.dropna()
        
        if len(ml_df) == 0:
            raise Exception("No data available after removing missing values")
        
        # Get setup parameters
        setup_params = get_pycaret_setup_params()
        
        if PYCARET_V3:
            # PyCaret 3.x approach
            clf_exp = ClassificationExperiment()
            clf_exp.setup(
                data=ml_df,
                target=target,
                **setup_params
            )
            
            # Compare models
            best_models = clf_exp.compare_models(
                include=['lr', 'rf', 'gbc', 'dt', 'nb'],
                sort='Accuracy',
                n_select=5,
                verbose=False
            )
            
            # Get results
            results_df = clf_exp.pull()
            
            # Finalize best model
            if isinstance(best_models, list):
                best_model = clf_exp.finalize_model(best_models[0])
            else:
                best_model = clf_exp.finalize_model(best_models)
            
        else:
            # PyCaret 2.x approach
            clf_setup(
                data=ml_df,
                target=target,
                **setup_params
            )
            
            # Compare models
            best_models = clf_compare(
                include=['lr', 'rf', 'gbc', 'dt', 'nb'],
                sort='Accuracy',
                n_select=5
            )
            
            # Get results
            results_df = clf_pull()
            
            # Finalize best model
            best_model = clf_finalize(best_models.iloc[0] if hasattr(best_models, 'iloc') else best_models)
        
        # Process results
        model_comparison = results_df.to_dict('records') if hasattr(results_df, 'to_dict') else []
        best_model_name = str(type(best_model).__name__)
        
        # Get best score
        if len(model_comparison) > 0:
            best_score = float(model_comparison[0].get('Accuracy', 0))
        else:
            best_score = 0.0
        
        # Feature importance
        feature_importance = get_feature_importance(best_model, features)
        
        return {
            'best_model': best_model_name,
            'best_score': best_score,
            'model_results': {
                'accuracy': best_score,
                'precision': float(model_comparison[0].get('Prec.', 0)) if model_comparison else 0,
                'recall': float(model_comparison[0].get('Recall', 0)) if model_comparison else 0,
                'f1': float(model_comparison[0].get('F1', 0)) if model_comparison else 0,
                'model_type': 'classification'
            },
            'model_comparison': model_comparison[:5],
            'feature_importance': feature_importance
        }
        
    except Exception as e:
        raise Exception(f"Error in classification experiment: {str(e)}")

def run_clustering_experiment_v2(df, experiment):
    """Run clustering experiment with version compatibility"""
    try:
        features = experiment.features
        
        # Prepare data
        ml_df = df[features].copy()
        ml_df = ml_df.dropna()
        
        if len(ml_df) == 0:
            raise Exception("No data available after removing missing values")
        
        # Get setup parameters
        setup_params = get_pycaret_setup_params()
        
        if PYCARET_V3:
            # PyCaret 3.x approach
            clust_exp = ClusteringExperiment()
            clust_exp.setup(
                data=ml_df,
                **setup_params
            )
            
            # Create clustering model
            kmeans_model = clust_exp.create_model('kmeans')
            
            # Get results
            results_df = clust_exp.pull()
            
        else:
            # PyCaret 2.x approach
            clust_setup(
                data=ml_df,
                **setup_params
            )
            
            # Create clustering model
            kmeans_model = clust_create('kmeans')
            
            # Get results
            results_df = clust_pull()
        
        # Process results
        silhouette_score = 0.5  # Default value
        if hasattr(results_df, 'loc'):
            try:
                silhouette_score = float(results_df.loc[results_df['Model'] == 'KMeans', 'Silhouette'].iloc[0])
            except:
                pass
        
        return {
            'best_model': 'KMeans',
            'best_score': silhouette_score,
            'model_results': {
                'silhouette_score': silhouette_score,
                'model_type': 'clustering',
                'n_clusters': getattr(kmeans_model, 'n_clusters', 8)
            },
            'model_comparison': [{'Model': 'KMeans', 'Silhouette': silhouette_score}],
            'feature_importance': {}
        }
        
    except Exception as e:
        raise Exception(f"Error in clustering experiment: {str(e)}")

def get_feature_importance(model, features):
    """Extract feature importance from trained model"""
    try:
        importance_dict = {}
        
        if hasattr(model, 'feature_importances_'):
            # Tree-based models
            importances = model.feature_importances_
            importance_dict = dict(zip(features, importances.tolist()))
            
        elif hasattr(model, 'coef_'):
            # Linear models
            coef = model.coef_
            if len(coef.shape) > 1:
                # Multi-class classification
                importances = np.abs(coef[0])
            else:
                # Binary classification or regression
                importances = np.abs(coef)
            importance_dict = dict(zip(features, importances.tolist()))
            
        elif hasattr(model, 'feature_importances'):
            # Some other models
            importances = model.feature_importances
            importance_dict = dict(zip(features, importances.tolist()))
            
        # Sort by importance
        importance_dict = dict(sorted(importance_dict.items(), key=lambda x: abs(x[1]), reverse=True))
        
        return importance_dict
        
    except Exception as e:
        print(f"Could not extract feature importance: {e}")
        return {}

def read_dataset(file_path):
    """Read dataset from file path with enhanced error handling"""
    try:
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.csv':
            # Try different encodings and separators for CSV files
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            separators = [',', ';', '\t']
            
            for encoding in encodings:
                for sep in separators:
                    try:
                        df = pd.read_csv(file_path, encoding=encoding, sep=sep)
                        # Check if dataframe is valid (has more than one column or reasonable data)
                        if len(df.columns) > 1 or len(df) > 0:
                            return df
                    except (UnicodeDecodeError, pd.errors.EmptyDataError, pd.errors.ParserError):
                        continue
            
            raise ValueError("Could not read CSV file with any supported encoding/separator combination")
            
        elif file_extension in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
            return df
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
            
    except Exception as e:
        raise Exception(f"Error reading dataset: {str(e)}")

# Fallback ML implementation using scikit-learn (if PyCaret fails)
def run_sklearn_fallback(df, experiment):
    """Fallback ML implementation using pure scikit-learn"""
    try:
        from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
        from sklearn.linear_model import LinearRegression, LogisticRegression
        from sklearn.cluster import KMeans
        from sklearn.metrics import mean_squared_error, accuracy_score, silhouette_score
        from sklearn.model_selection import train_test_split
        from sklearn.preprocessing import LabelEncoder
        
        if experiment.ml_type == 'regression':
            target = experiment.target_variable
            features = experiment.features
            
            # Prepare data
            X = df[features]
            y = df[target]
            
            # Remove missing values
            mask = ~(X.isnull().any(axis=1) | y.isnull())
            X = X[mask]
            y = y[mask]
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Train models
            models = {
                'LinearRegression': LinearRegression(),
                'RandomForestRegressor': RandomForestRegressor(n_estimators=100, random_state=42)
            }
            
            best_score = float('inf')
            best_model_name = 'LinearRegression'
            best_model = None
            
            for name, model in models.items():
                model.fit(X_train, y_train)
                y_pred = model.predict(X_test)
                rmse = np.sqrt(mean_squared_error(y_test, y_pred))
                
                if rmse < best_score:
                    best_score = rmse
                    best_model_name = name
                    best_model = model
            
            # Feature importance
            feature_importance = get_feature_importance(best_model, features)
            
            return {
                'best_model': best_model_name,
                'best_score': best_score,
                'model_results': {
                    'rmse': best_score,
                    'model_type': 'regression'
                },
                'model_comparison': [{'Model': best_model_name, 'RMSE': best_score}],
                'feature_importance': feature_importance
            }
            
        elif experiment.ml_type == 'classification':
            target = experiment.target_variable
            features = experiment.features
            
            # Prepare data
            X = df[features]
            y = df[target]
            
            # Remove missing values
            mask = ~(X.isnull().any(axis=1) | y.isnull())
            X = X[mask]
            y = y[mask]
            
            # Encode target if necessary
            if y.dtype == 'object':
                le = LabelEncoder()
                y = le.fit_transform(y)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Train models
            models = {
                'LogisticRegression': LogisticRegression(random_state=42, max_iter=1000),
                'RandomForestClassifier': RandomForestClassifier(n_estimators=100, random_state=42)
            }
            
            best_score = 0
            best_model_name = 'LogisticRegression'
            best_model = None
            
            for name, model in models.items():
                model.fit(X_train, y_train)
                y_pred = model.predict(X_test)
                accuracy = accuracy_score(y_test, y_pred)
                
                if accuracy > best_score:
                    best_score = accuracy
                    best_model_name = name
                    best_model = model
            
            # Feature importance
            feature_importance = get_feature_importance(best_model, features)
            
            return {
                'best_model': best_model_name,
                'best_score': best_score,
                'model_results': {
                    'accuracy': best_score,
                    'model_type': 'classification'
                },
                'model_comparison': [{'Model': best_model_name, 'Accuracy': best_score}],
                'feature_importance': feature_importance
            }
            
        elif experiment.ml_type == 'clustering':
            features = experiment.features
            
            # Prepare data
            X = df[features].dropna()
            
            # Train KMeans
            kmeans = KMeans(n_clusters=3, random_state=42)
            labels = kmeans.fit_predict(X)
            
            # Calculate silhouette score
            sil_score = silhouette_score(X, labels)
            
            return {
                'best_model': 'KMeans',
                'best_score': sil_score,
                'model_results': {
                    'silhouette_score': sil_score,
                    'model_type': 'clustering',
                    'n_clusters': 3
                },
                'model_comparison': [{'Model': 'KMeans', 'Silhouette': sil_score}],
                'feature_importance': {}
            }
            
    except Exception as e:
        raise Exception(f"Fallback ML implementation failed: {str(e)}")

# Enhanced experiment runner with fallback
def run_ml_experiment_with_fallback(experiment):
    """Run ML experiment with PyCaret, fallback to scikit-learn if needed"""
    try:
        # First try PyCaret
        if PYCARET_AVAILABLE:
            return run_ml_experiment(experiment)
        else:
            raise Exception("PyCaret not available")
            
    except Exception as pycaret_error:
        print(f"PyCaret failed: {pycaret_error}")
        print("Falling back to scikit-learn implementation...")
        
        try:
            # Fallback to scikit-learn
            df = read_dataset(experiment.dataset.file.path)
            return run_sklearn_fallback(df, experiment)
            
        except Exception as fallback_error:
            raise Exception(f"Both PyCaret and fallback failed. PyCaret: {pycaret_error}, Fallback: {fallback_error}")

# Test PyCaret installation and version
def test_pycaret_installation():
    """Test PyCaret installation and return configuration info"""
    info = {
        'available': PYCARET_AVAILABLE,
        'version': PYCARET_VERSION if PYCARET_AVAILABLE else None,
        'api_version': '3.x' if PYCARET_V3 else '2.x' if PYCARET_AVAILABLE else None,
        'setup_params': get_pycaret_setup_params() if PYCARET_AVAILABLE else {}
    }
    return info
  
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
import plotly.utils
import io
import base64
import json
from datetime import datetime
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
import warnings
warnings.filterwarnings('ignore')

# Try to import PyCaret
try:
    import pycaret
    from pycaret.regression import setup as reg_setup, compare_models as reg_compare, finalize_model as reg_finalize, pull as reg_pull
    from pycaret.classification import setup as clf_setup, compare_models as clf_compare, finalize_model as clf_finalize, pull as clf_pull
    from pycaret.clustering import setup as clust_setup, create_model as clust_create, pull as clust_pull
    PYCARET_AVAILABLE = True
except ImportError:
    PYCARET_AVAILABLE = False
    print("PyCaret not available. Install with: pip install pycaret")

def read_dataset(file_path):
    """Read dataset from file path"""
    try:
        if file_path.lower().endswith('.csv'):
            df = pd.read_csv(file_path)
        elif file_path.lower().endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file_path)
        else:
            raise ValueError("Unsupported file format")
        return df
    except Exception as e:
        raise Exception(f"Error reading file: {str(e)}")

def perform_eda(file_path):
    """Perform comprehensive EDA on the dataset"""
    
    df = read_dataset(file_path)
    eda_results = {}
    
    # Basic information
    eda_results['basic_info'] = {
        'shape': df.shape,
        'columns': df.columns.tolist(),
        'dtypes': df.dtypes.astype(str).to_dict(),
        'memory_usage': int(df.memory_usage(deep=True).sum())
    }
    
    # Summary statistics
    summary_stats = {}
    numeric_summary = df.describe(include=[np.number])
    categorical_summary = df.describe(include=['object'])
    
    if not numeric_summary.empty:
        summary_stats['numeric'] = numeric_summary.to_dict()
    if not categorical_summary.empty:
        summary_stats['categorical'] = categorical_summary.to_dict()
    
    eda_results['summary_stats'] = summary_stats
    
    # Column information
    column_info = {}
    for col in df.columns:
        col_data = df[col]
        null_count = int(col_data.isnull().sum())
        null_percentage = float(null_count / len(df) * 100)
        unique_count = int(col_data.nunique())
        unique_percentage = float(unique_count / len(df) * 100)
        
        column_info[col] = {
            'dtype': str(col_data.dtype),
            'null_count': null_count,
            'null_percentage': round(null_percentage, 2),
            'unique_count': unique_count,
            'unique_percentage': round(unique_percentage, 2),
            'sample_values': col_data.dropna().head(5).tolist()
        }
        
        if col_data.dtype in ['int64', 'float64']:
            if not col_data.isnull().all():
                column_info[col].update({
                    'mean': float(col_data.mean()),
                    'std': float(col_data.std()),
                    'min': float(col_data.min()),
                    'max': float(col_data.max()),
                    'median': float(col_data.median()),
                    'skewness': float(col_data.skew()),
                    'kurtosis': float(col_data.kurtosis())
                })
    
    eda_results['column_info'] = column_info
    
    # Univariate analysis
    univariate = {}
    for col in df.columns:
        col_data = df[col].dropna()
        
        if col_data.dtype in ['int64', 'float64']:
            univariate[col] = {
                'type': 'numerical',
                'distribution_stats': {
                    'mean': float(col_data.mean()),
                    'median': float(col_data.median()),
                    'mode': float(col_data.mode().iloc[0]) if not col_data.mode().empty else None,
                    'std': float(col_data.std()),
                    'variance': float(col_data.var()),
                    'range': float(col_data.max() - col_data.min()),
                    'iqr': float(col_data.quantile(0.75) - col_data.quantile(0.25))
                },
                'outliers': detect_outliers(col_data)
            }
        else:
            value_counts = col_data.value_counts().head(20)
            univariate[col] = {
                'type': 'categorical',
                'value_counts': value_counts.to_dict(),
                'top_categories': value_counts.index.tolist()[:10]
            }
    
    eda_results['univariate'] = univariate
    
    # Correlation analysis
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) > 1:
        correlation_matrix = df[numeric_cols].corr()
        eda_results['correlation'] = correlation_matrix.to_dict()
        
        # Find highly correlated pairs
        high_corr_pairs = []
        for i in range(len(correlation_matrix.columns)):
            for j in range(i+1, len(correlation_matrix.columns)):
                corr_val = correlation_matrix.iloc[i, j]
                if abs(corr_val) > 0.7:
                    high_corr_pairs.append({
                        'var1': correlation_matrix.columns[i],
                        'var2': correlation_matrix.columns[j],
                        'correlation': float(corr_val)
                    })
        
        eda_results['high_correlations'] = high_corr_pairs
    else:
        eda_results['correlation'] = {}
        eda_results['high_correlations'] = []
    
    # Multivariate analysis
    multivariate = {
        'categorical_relationships': {},
        'numeric_categorical_relationships': {}
    }
    
    # Analyze relationships between categorical variables
    categorical_cols = df.select_dtypes(include=['object']).columns
    if len(categorical_cols) > 1:
        for i, cat1 in enumerate(categorical_cols):
            for cat2 in categorical_cols[i+1:]:
                try:
                    crosstab = pd.crosstab(df[cat1], df[cat2])
                    if crosstab.size > 0 and crosstab.size <= 100:  # Avoid huge crosstabs
                        multivariate['categorical_relationships'][f'{cat1}_vs_{cat2}'] = crosstab.to_dict()
                except:
                    pass
    
    eda_results['multivariate'] = multivariate
    
    # Data quality issues
    data_quality = check_data_quality(df)
    eda_results['data_quality'] = data_quality
    
    return eda_results

def detect_outliers(series):
    """Detect outliers using IQR method"""
    if series.dtype not in ['int64', 'float64'] or len(series) == 0:
        return {'count': 0, 'percentage': 0.0}
    
    Q1 = series.quantile(0.25)
    Q3 = series.quantile(0.75)
    IQR = Q3 - Q1
    
    if IQR == 0:
        return {'count': 0, 'percentage': 0.0}
    
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    
    outliers = series[(series < lower_bound) | (series > upper_bound)]
    
    return {
        'count': len(outliers),
        'percentage': round(len(outliers) / len(series) * 100, 2),
        'lower_bound': float(lower_bound),
        'upper_bound': float(upper_bound),
        'outlier_values': outliers.head(10).tolist() if len(outliers) > 0 else []
    }

def check_data_quality(df):
    """Check for data quality issues that may impact performance"""
    issues = {
        'missing_data': {},
        'duplicates': {},
        'data_types': {},
        'high_cardinality': {},
        'performance_warnings': []
    }
    
    # Missing data analysis
    missing_data = df.isnull().sum()
    total_missing = int(missing_data.sum())
    missing_percentage = round(total_missing / (len(df) * len(df.columns)) * 100, 2)
    
    issues['missing_data'] = {
        'total_missing': total_missing,
        'columns_with_missing': {col: int(count) for col, count in missing_data[missing_data > 0].items()},
        'percentage_missing': missing_percentage,
        'missing_percentage_by_column': {col: round(count/len(df)*100, 2) for col, count in missing_data[missing_data > 0].items()}
    }
    
    # Duplicate analysis
    duplicate_count = int(df.duplicated().sum())
    duplicate_percentage = round(duplicate_count / len(df) * 100, 2)
    
    issues['duplicates'] = {
        'count': duplicate_count,
        'percentage': duplicate_percentage
    }
    
    # Data type issues
    mixed_types = []
    for col in df.columns:
        if df[col].dtype == 'object':
            sample_values = df[col].dropna().head(100)
            if len(sample_values) > 0:
                types = set(type(val).__name__ for val in sample_values)
                if len(types) > 1:
                    mixed_types.append({
                        'column': col,
                        'types_found': list(types)
                    })
    
    issues['data_types'] = {
        'mixed_types': mixed_types
    }
    
    # High cardinality analysis
    high_cardinality_cols = []
    for col in df.columns:
        unique_ratio = df[col].nunique() / len(df)
        if df[col].dtype == 'object' and df[col].nunique() > 50 and unique_ratio > 0.9:
            high_cardinality_cols.append({
                'column': col,
                'unique_count': int(df[col].nunique()),
                'unique_ratio': round(unique_ratio, 3)
            })
    
    issues['high_cardinality'] = {
        'columns': high_cardinality_cols
    }
    
    # Performance warnings
    warnings = []
    
    if len(df) > 100000:
        warnings.append({
            'type': 'large_dataset',
            'message': f"Large dataset ({len(df):,} rows) - ML training may take longer",
            'severity': 'medium'
        })
    
    if len(df.columns) > 100:
        warnings.append({
            'type': 'high_dimensionality',
            'message': f"High dimensionality ({len(df.columns)} columns) - consider feature selection",
            'severity': 'medium'
        })
    
    if missing_percentage > 20:
        warnings.append({
            'type': 'high_missing_data',
            'message': f"High missing data percentage ({missing_percentage}%) - may impact model performance",
            'severity': 'high'
        })
    
    if duplicate_percentage > 10:
        warnings.append({
            'type': 'high_duplicates',
            'message': f"High duplicate percentage ({duplicate_percentage}%) - consider deduplication",
            'severity': 'medium'
        })
    
    if len(high_cardinality_cols) > 0:
        warnings.append({
            'type': 'high_cardinality',
            'message': f"High cardinality categorical columns detected - may cause memory issues",
            'severity': 'medium'
        })
    
    issues['performance_warnings'] = warnings
    
    return issues

def generate_plots(file_path):
    """Generate visualization plots for EDA"""
    df = read_dataset(file_path)
    plots = {}
    
    try:
        # Set style for matplotlib
        plt.style.use('default')
        sns.set_palette("husl")
        
        # 1. Correlation heatmap (if numeric columns exist)
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 1:
            fig, ax = plt.subplots(figsize=(10, 8))
            correlation_matrix = df[numeric_cols].corr()
            
            # Create heatmap
            mask = np.triu(np.ones_like(correlation_matrix, dtype=bool))
            sns.heatmap(correlation_matrix, mask=mask, annot=True, cmap='coolwarm', 
                       center=0, square=True, fmt='.2f', cbar_kws={"shrink": .5})
            plt.title('Correlation Matrix', fontsize=14, fontweight='bold')
            plt.tight_layout()
            
            # Convert to base64
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            image_png = buffer.getvalue()
            buffer.close()
            plots['correlation_heatmap'] = base64.b64encode(image_png).decode()
            plt.close()
        
        # 2. Distribution plots for numeric columns
        if len(numeric_cols) > 0:
            n_cols = min(4, len(numeric_cols))
            n_rows = (len(numeric_cols) + n_cols - 1) // n_cols
            
            fig, axes = plt.subplots(n_rows, n_cols, figsize=(15, 5*n_rows))
            if n_rows == 1:
                axes = [axes] if n_cols == 1 else axes
            else:
                axes = axes.flatten()
            
            for i, col in enumerate(numeric_cols):
                if i < len(axes):
                    df[col].hist(bins=30, ax=axes[i], alpha=0.7, color='skyblue', edgecolor='black')
                    axes[i].set_title(f'Distribution of {col}', fontweight='bold')
                    axes[i].set_xlabel(col)
                    axes[i].set_ylabel('Frequency')
                    axes[i].grid(True, alpha=0.3)
            
            # Hide empty subplots
            for i in range(len(numeric_cols), len(axes)):
                axes[i].set_visible(False)
            
            plt.tight_layout()
            
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            image_png = buffer.getvalue()
            buffer.close()
            plots['distributions'] = base64.b64encode(image_png).decode()
            plt.close()
        
        # 3. Missing data visualization
        missing_data = df.isnull().sum()
        if missing_data.sum() > 0:
            fig, ax = plt.subplots(figsize=(12, 6))
            missing_data[missing_data > 0].plot(kind='bar', ax=ax, color='coral')
            plt.title('Missing Data by Column', fontsize=14, fontweight='bold')
            plt.xlabel('Columns')
            plt.ylabel('Missing Count')
            plt.xticks(rotation=45)
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            image_png = buffer.getvalue()
            buffer.close()
            plots['missing_data'] = base64.b64encode(image_png).decode()
            plt.close()
        
        # 4. Box plots for outlier detection
        if len(numeric_cols) > 0:
            n_cols = min(3, len(numeric_cols))
            n_rows = (len(numeric_cols) + n_cols - 1) // n_cols
            
            fig, axes = plt.subplots(n_rows, n_cols, figsize=(15, 5*n_rows))
            if n_rows == 1:
                axes = [axes] if n_cols == 1 else axes
            else:
                axes = axes.flatten()
            
            for i, col in enumerate(numeric_cols):
                if i < len(axes):
                    df.boxplot(column=col, ax=axes[i])
                    axes[i].set_title(f'Box Plot - {col}', fontweight='bold')
                    axes[i].grid(True, alpha=0.3)
            
            # Hide empty subplots
            for i in range(len(numeric_cols), len(axes)):
                axes[i].set_visible(False)
            
            plt.tight_layout()
            
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            image_png = buffer.getvalue()
            buffer.close()
            plots['boxplots'] = base64.b64encode(image_png).decode()
            plt.close()
    
    except Exception as e:
        print(f"Error generating plots: {str(e)}")
    
    return plots

def run_ml_experiment(experiment):
    """Run machine learning experiment using PyCaret"""
    if not PYCARET_AVAILABLE:
        raise Exception("PyCaret is not available. Please install it to run ML experiments.")
    
    # Read dataset
    df = read_dataset(experiment.dataset.file.path)
    
    # Update experiment status
    experiment.status = 'running'
    experiment.save()
    
    results = {
        'best_model': '',
        'best_score': 0.0,
        'model_results': {},
        'feature_importance': {},
        'model_comparison': {}
    }
    
    try:
        if experiment.ml_type == 'regression':
            results = run_regression_experiment(df, experiment)
        elif experiment.ml_type == 'classification':
            results = run_classification_experiment(df, experiment)
        elif experiment.ml_type == 'clustering':
            results = run_clustering_experiment(df, experiment)
        elif experiment.ml_type == 'anomaly':
            results = run_anomaly_detection(df, experiment)
        
        experiment.status = 'completed'
        experiment.completed_at = datetime.now()
        
    except Exception as e:
        experiment.status = 'failed'
        experiment.error_message = str(e)
        raise e
    finally:
        experiment.save()
    
    return results

def run_regression_experiment(df, experiment):
    """Run regression experiment"""
    target = experiment.target_variable
    features = experiment.features
    
    # Prepare data
    ml_df = df[features + [target]].copy()
    ml_df = ml_df.dropna()
    
    # Setup PyCaret
    reg_setup(ml_df, target=target, session_id=123, train_size=0.8, 
              silent=True, verbose=False)
    
    # Compare models
    best_models = reg_compare(sort='RMSE', n_select=5)
    
    # Get model comparison results
    model_comparison = reg_pull().to_dict('records')
    
    # Finalize best model
    best_model = reg_finalize(best_models.iloc[0])
    
    # Get feature importance (if available)
    feature_importance = {}
    try:
        if hasattr(best_model, 'feature_importances_'):
            importance_scores = best_model.feature_importances_
            feature_importance = dict(zip(features, importance_scores.tolist()))
        elif hasattr(best_model, 'coef_'):
            importance_scores = abs(best_model.coef_)
            feature_importance = dict(zip(features, importance_scores.tolist()))
    except:
        pass
    
    return {
        'best_model': str(type(best_model).__name__),
        'best_score': float(model_comparison[0].get('RMSE', 0)),
        'model_results': {
            'r2_score': float(model_comparison[0].get('R2', 0)),
            'mae': float(model_comparison[0].get('MAE', 0)),
            'rmse': float(model_comparison[0].get('RMSE', 0)),
            'mse': float(model_comparison[0].get('MSE', 0))
        },
        'feature_importance': feature_importance,
        'model_comparison': model_comparison[:5]  # Top 5 models
    }

def run_classification_experiment(df, experiment):
    """Run classification experiment"""
    target = experiment.target_variable
    features = experiment.features
    
    # Prepare data
    ml_df = df[features + [target]].copy()
    ml_df = ml_df.dropna()
    
    # Setup PyCaret
    clf_setup(ml_df, target=target, session_id=123, train_size=0.8,
              silent=True, verbose=False)
    
    # Compare models
    best_models = clf_compare(sort='Accuracy', n_select=5)
    
    # Get model comparison results
    model_comparison = clf_pull().to_dict('records')
    
    # Finalize best model
    best_model = clf_finalize(best_models.iloc[0])
    
    # Get feature importance
    feature_importance = {}
    try:
        if hasattr(best_model, 'feature_importances_'):
            importance_scores = best_model.feature_importances_
            feature_importance = dict(zip(features, importance_scores.tolist()))
        elif hasattr(best_model, 'coef_'):
            if len(best_model.coef_.shape) > 1:
                importance_scores = abs(best_model.coef_[0])
            else:
                importance_scores = abs(best_model.coef_)
            feature_importance = dict(zip(features, importance_scores.tolist()))
    except:
        pass
    
    return {
        'best_model': str(type(best_model).__name__),
        'best_score': float(model_comparison[0].get('Accuracy', 0)),
        'model_results': {
            'accuracy': float(model_comparison[0].get('Accuracy', 0)),
            'precision': float(model_comparison[0].get('Prec.', 0)),
            'recall': float(model_comparison[0].get('Recall', 0)),
            'f1_score': float(model_comparison[0].get('F1', 0)),
            'auc': float(model_comparison[0].get('AUC', 0))
        },
        'feature_importance': feature_importance,
        'model_comparison': model_comparison[:5]
    }

def run_clustering_experiment(df, experiment):
    """Run clustering experiment"""
    features = experiment.features
    
    # Prepare data
    ml_df = df[features].copy()
    ml_df = ml_df.dropna()
    
    # Setup PyCaret
    clust_setup(ml_df, session_id=123, silent=True, verbose=False)
    
    # Create clustering models
    kmeans = clust_create('kmeans')
    
    # Get clustering results
    cluster_results = clust_pull()
    
    return {
        'best_model': 'KMeans',
        'best_score': float(cluster_results.get('Silhouette', 0)),
        'model_results': {
            'silhouette_score': float(cluster_results.get('Silhouette', 0)),
            'calinski_harabasz': float(cluster_results.get('Calinski-Harabasz', 0)),
            'davies_bouldin': float(cluster_results.get('Davies-Bouldin', 0))
        },
        'feature_importance': {},
        'model_comparison': [cluster_results.to_dict()]
    }

def run_anomaly_detection(df, experiment):
    """Run anomaly detection"""
    features = experiment.features
    
    # For now, use simple statistical method
    ml_df = df[features].copy()
    ml_df = ml_df.dropna()
    
    # Simple isolation forest approach
    from sklearn.ensemble import IsolationForest
    
    model = IsolationForest(contamination=0.1, random_state=123)
    predictions = model.fit_predict(ml_df)
    
    anomaly_count = sum(predictions == -1)
    anomaly_percentage = anomaly_count / len(predictions) * 100
    
    return {
        'best_model': 'IsolationForest',
        'best_score': float(anomaly_percentage),
        'model_results': {
            'anomaly_count': int(anomaly_count),
            'anomaly_percentage': float(anomaly_percentage),
            'normal_count': int(sum(predictions == 1))
        },
        'feature_importance': {},
        'model_comparison': [{
            'Model': 'Isolation Forest',
            'Anomaly_Percentage': float(anomaly_percentage)
        }]
    }

def read_dataset(file_path):
    """Read dataset from file path with error handling"""
    try:
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.csv':
            # Try different encodings for CSV files
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            for encoding in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=encoding)
                    return df
                except UnicodeDecodeError:
                    continue
            raise ValueError("Could not read CSV file with any supported encoding")
            
        elif file_extension in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
            return df
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
            
    except Exception as e:
        raise Exception(f"Error reading dataset: {str(e)}")
    
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import Dict, List, Optional

class LoanAmortizationCalculator:
    """Loan amortization calculator for Django integration"""
    
    def __init__(self):
        self.loan_params = {}
        self.amortization_schedule = []
        
    def setup_loan(self, 
                   principal: float,
                   annual_rate: float,
                   term_months: int,
                   start_date: str = None,
                   loan_type: str = "fixed",
                   payment_frequency: str = "monthly",
                   grace_period_months: int = 0,
                   interest_only_months: int = 0,
                   deferred_months: int = 0,
                   balloon_payment: float = 0,
                   compound_frequency: str = "monthly",
                   late_fee: float = 0,
                   late_fee_grace_days: int = 15,
                   prepayment_penalty_rate: float = 0,
                   variable_rate_schedule: List[Dict] = None,
                   extra_payments: List[Dict] = None):
        
        self.loan_params = {
            'principal': principal,
            'annual_rate': annual_rate,
            'term_months': term_months,
            'start_date': datetime.strptime(start_date, '%Y-%m-%d') if start_date else datetime.now(),
            'loan_type': loan_type,
            'payment_frequency': payment_frequency,
            'grace_period_months': grace_period_months,
            'interest_only_months': interest_only_months,
            'deferred_months': deferred_months,
            'balloon_payment': balloon_payment,
            'compound_frequency': compound_frequency,
            'late_fee': late_fee,
            'late_fee_grace_days': late_fee_grace_days,
            'prepayment_penalty_rate': prepayment_penalty_rate,
            'variable_rate_schedule': variable_rate_schedule or [],
            'extra_payments': extra_payments or []
        }
        
        # Calculate payment frequency multiplier
        freq_map = {
            'monthly': 12,
            'weekly': 52,
            'bi_weekly': 26,
            'quarterly': 4
        }
        self.loan_params['payments_per_year'] = freq_map[payment_frequency]
        
    def calculate_payment_amount(self, principal: float, rate: float, periods: int) -> float:
        """Calculate standard loan payment using PMT formula."""
        if rate == 0:
            return principal / periods
        
        monthly_rate = rate / self.loan_params['payments_per_year']
        payment = principal * (monthly_rate * (1 + monthly_rate)**periods) / ((1 + monthly_rate)**periods - 1)
        return payment
    
    def get_current_rate(self, period: int) -> float:
        """Get current interest rate considering variable rate schedule."""
        current_rate = self.loan_params['annual_rate']
        
        for rate_change in self.loan_params['variable_rate_schedule']:
            if period >= rate_change['month']:
                current_rate = rate_change['rate']
            else:
                break
                
        return current_rate
    
    def calculate_interest(self, balance: float, rate: float) -> float:
        """Calculate interest for the period."""
        period_rate = rate / self.loan_params['payments_per_year']
        return balance * period_rate
    
    def get_extra_payment(self, period: int) -> float:
        """Get extra payment amount for the period."""
        for extra in self.loan_params['extra_payments']:
            if extra['month'] == period:
                return extra['amount']
        return 0
    
    def generate_amortization_schedule(self) -> pd.DataFrame:
        """Generate comprehensive amortization schedule."""
        schedule = []
        
        # Initialize variables
        remaining_balance = self.loan_params['principal']
        current_date = self.loan_params['start_date']
        
        # Calculate base payment amount
        regular_periods = (self.loan_params['term_months'] - 
                          self.loan_params['interest_only_months'] - 
                          self.loan_params['deferred_months'])
        
        # Adjust for payment frequency
        if self.loan_params['payment_frequency'] == 'monthly':
            date_increment = relativedelta(months=1)
        elif self.loan_params['payment_frequency'] == 'weekly':
            date_increment = timedelta(weeks=1)
            regular_periods = regular_periods * 52 / 12
        elif self.loan_params['payment_frequency'] == 'bi_weekly':
            date_increment = timedelta(weeks=2)
            regular_periods = regular_periods * 26 / 12
        elif self.loan_params['payment_frequency'] == 'quarterly':
            date_increment = relativedelta(months=3)
            regular_periods = regular_periods / 3
        
        regular_periods = int(regular_periods)
        
        # Calculate total periods
        total_periods = self.loan_params['term_months']
        if self.loan_params['payment_frequency'] != 'monthly':
            total_periods = int(total_periods * self.loan_params['payments_per_year'] / 12)
        
        # Generate schedule
        for period in range(1, total_periods + 1):
            current_rate = self.get_current_rate(period)
            interest_payment = self.calculate_interest(remaining_balance, current_rate)
            
            # Determine payment type based on period
            if period <= self.loan_params['grace_period_months']:
                payment_amount = 0
                principal_payment = 0
                payment_type = "Grace Period"
                
            elif period <= (self.loan_params['grace_period_months'] + 
                           self.loan_params['deferred_months']):
                payment_amount = 0
                principal_payment = -interest_payment
                remaining_balance += interest_payment
                payment_type = "Deferred"
                
            elif period <= (self.loan_params['grace_period_months'] + 
                           self.loan_params['deferred_months'] + 
                           self.loan_params['interest_only_months']):
                payment_amount = interest_payment
                principal_payment = 0
                payment_type = "Interest Only"
                
            else:
                # Regular amortizing payments
                if self.loan_params['loan_type'] == 'balloon' and period == total_periods:
                    payment_amount = remaining_balance + interest_payment + self.loan_params['balloon_payment']
                    principal_payment = remaining_balance
                    payment_type = "Balloon Payment"
                else:
                    remaining_regular_periods = (total_periods - period + 1 - 
                                               len([p for p in range(period, total_periods + 1) 
                                                   if p <= self.loan_params['grace_period_months'] + 
                                                   self.loan_params['deferred_months'] + 
                                                   self.loan_params['interest_only_months']]))
                    
                    if remaining_regular_periods > 0:
                        base_payment = self.calculate_payment_amount(
                            remaining_balance, current_rate, remaining_regular_periods)
                        principal_payment = base_payment - interest_payment
                        payment_amount = base_payment
                        payment_type = "Regular"
                    else:
                        payment_amount = remaining_balance + interest_payment
                        principal_payment = remaining_balance
                        payment_type = "Final Payment"
            
            # Add extra payments
            extra_payment = self.get_extra_payment(period)
            if extra_payment > 0:
                payment_amount += extra_payment
                principal_payment += extra_payment
                payment_type += " + Extra"
            
            # Update remaining balance
            remaining_balance -= principal_payment
            remaining_balance = max(0, remaining_balance)
            
            # Calculate cumulative totals
            cumulative_interest = sum([row['Interest_Payment'] for row in schedule]) + interest_payment
            cumulative_principal = sum([row['Principal_Payment'] for row in schedule]) + principal_payment
            
            # Add to schedule
            schedule.append({
                'Period': period,
                'Date': current_date.strftime('%Y-%m-%d'),
                'Beginning_Balance': remaining_balance + principal_payment,
                'Payment_Amount': round(payment_amount, 2),
                'Interest_Payment': round(interest_payment, 2),
                'Principal_Payment': round(principal_payment, 2),
                'Extra_Payment': round(extra_payment, 2),
                'Ending_Balance': round(remaining_balance, 2),
                'Cumulative_Interest': round(cumulative_interest, 2),
                'Cumulative_Principal': round(cumulative_principal, 2),
                'Current_Rate': round(current_rate * 100, 4),
                'Payment_Type': payment_type
            })
            
            # Break if loan is paid off
            if remaining_balance <= 0.01:
                break
                
            # Increment date
            current_date += date_increment
        
        self.amortization_schedule = schedule
        return pd.DataFrame(schedule)

from django import forms
from django.db.models import Q
from django.core.exceptions import ValidationError
import json

class CascadeFormMixin:
    """Mixin to handle cascade selection logic"""
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.setup_cascade_fields()
    
    def setup_cascade_fields(self):
        """Setup cascade field dependencies"""
        cascade_fields = getattr(self, 'cascade_fields', {})
        for target_field, source_field in cascade_fields.items():
            if source_field in self.data:
                try:
                    source_value = self.data.get(source_field)
                    if source_value:
                        self.filter_choices(target_field, source_field, source_value)
                except (ValueError, TypeError):
                    pass
    
    def filter_choices(self, target_field, source_field, source_value):
        """Filter choices based on source field value"""
        if hasattr(self, f'filter_{target_field}_choices'):
            getattr(self, f'filter_{target_field}_choices')(source_value)

class AjaxChoiceField(forms.ChoiceField):
    """Choice field that supports AJAX loading of options"""
    
    def __init__(self, ajax_url=None, *args, **kwargs):
        self.ajax_url = ajax_url
        super().__init__(*args, **kwargs)
    
    def widget_attrs(self, widget):
        attrs = super().widget_attrs(widget)
        if self.ajax_url:
            attrs['data-ajax-url'] = self.ajax_url
            attrs['data-ajax-enabled'] = 'true'
        return attrs

class DateRangeWidget(forms.MultiWidget):
    """Widget for date range selection"""
    
    def __init__(self, attrs=None):
        widgets = [
            forms.DateInput(attrs={'type': 'date', 'placeholder': 'Start Date'}),
            forms.DateInput(attrs={'type': 'date', 'placeholder': 'End Date'})
        ]
        super().__init__(widgets, attrs)
    
    def decompress(self, value):
        if value:
            return [value.get('start'), value.get('end')]
        return [None, None]

class DateRangeField(forms.MultiValueField):
    """Field for date range selection"""
    
    widget = DateRangeWidget
    
    def __init__(self, *args, **kwargs):
        fields = [
            forms.DateField(required=False),
            forms.DateField(required=False)
        ]
        super().__init__(fields, *args, **kwargs)
    
    def compress(self, data_list):
        if data_list:
            return {'start': data_list[0], 'end': data_list[1]}
        return {}

class JSONEditorWidget(forms.Textarea):
    """Widget for JSON field editing with validation"""
    
    def __init__(self, attrs=None):
        default_attrs = {
            'class': 'json-editor',
            'rows': 4,
            'style': 'font-family: monospace;'
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)
    
    def format_value(self, value):
        if value is None:
            return ''
        if isinstance(value, str):
            return value
        return json.dumps(value, indent=2)
LANGUAGES = [
            ('en', _('English')),
            ('es', _('Spanish')),
            ('fr', _('French')),
            ('de', _('German')),
            ('zh-hans', _('Chinese (Simplified)')),
        ] 
TIME_ZONES = [
            ('UTC', 'UTC'),
            ('US/Eastern', 'US/Eastern'),
            ('US/Central', 'US/Central'),
            ('US/Pacific', 'US/Pacific'),
            ('Europe/London', 'Europe/London'),
            ('Europe/Paris', 'Europe/Paris'),
            ('Asia/Tokyo', 'Asia/Tokyo'),
            ('Asia/Singapore', 'Asia/Singapore'),
        ]

import threading
from django.utils.deprecation import MiddlewareMixin

# Thread-local storage for organization context
_thread_locals = threading.local()

def get_current_organization():
    """Get current organization from thread-local storage"""
    return getattr(_thread_locals, 'organization', None)

def get_current_organization_id():
    """Get current organization ID from thread-local storage"""
    organization = get_current_organization()
    return organization.id if organization else None

def set_current_organization(organization):
    """Set current organization in thread-local storage"""
    _thread_locals.organization = organization

class OrganizationMiddleware(MiddlewareMixin):
    """Middleware to set organization context from session"""
    
    def process_request(self, request):
        # Clear any previous organization context
        set_current_organization(None)
        
        # Get organization from session
        org_id = request.session.get('active_organization_id')
        if org_id:
            try:
                from core.models import Organization
                organization = Organization.objects.get(pk=org_id)
                set_current_organization(organization)
            except Organization.DoesNotExist:
                pass
        
        return None