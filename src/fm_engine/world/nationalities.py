"""Dati anagrafici per la generazione del Mondo: nazionalita' e pool di nomi.

Le nazionalita' sono codici ISO 3166-1 alpha-2 minuscoli (forma canonica
del progetto, coerente con la colonna drivers.nationality dello schema DB):
la TUI ne deriva la bandiera, NATION_NAMES fornisce il nome leggibile.

I pesi delle nazionalita' riflettono i vivai reali del motorsport (Regno
Unito, Italia, Francia, Germania, Spagna, Brasile, Giappone, Paesi Bassi,
Australia, piu' code lunghe). Sono parametri di partenza tarabili: la
WorldConfig li espone come default sovrascrivibile.

I piloti generati possono essere uomini o donne (scelta esplicita di gioco,
si discosta dalla griglia reale): per ogni nazionalita' il pool di nomi
propri e' separato per genere, mentre i cognomi sono condivisi. Il genere
scelto in generazione seleziona il pool di nomi propri coerente.

Tutti i nomi sono di fantasia. A valle restano semplici stringhe editabili
via DB (Studio), come da convenzione di FOR-3.
"""

# I due generi usati nella generazione: i piloti possono essere uomini o
# donne. Il genere scelto seleziona il pool di nomi propri coerente; il pool
# di cognomi e' condiviso fra i generi.
GENDER_MALE = "male"
GENDER_FEMALE = "female"
GENDERS: tuple[str, ...] = (GENDER_MALE, GENDER_FEMALE)

# Human-readable name of each nationality, indexed by ISO code.
NATION_NAMES: dict[str, str] = {
    "gb": "Regno Unito",
    "it": "Italia",
    "fr": "Francia",
    "de": "Germania",
    "es": "Spagna",
    "br": "Brasile",
    "jp": "Giappone",
    "nl": "Paesi Bassi",
    "au": "Australia",
    "us": "Stati Uniti",
    "fi": "Finlandia",
    "mx": "Messico",
    "ca": "Canada",
    "dk": "Danimarca",
    "ar": "Argentina",
    "mc": "Monaco",
    "ch": "Svizzera",
    "at": "Austria",
    "be": "Belgio",
    "se": "Svezia",
    "nz": "Nuova Zelanda",
    "th": "Thailandia",
    "cn": "Cina",
}

# Relative weight of each nationality (ISO code) when drawing drivers.
# Tuned on real talent pools: the higher the weight, the more likely.
NATIONALITY_WEIGHTS: tuple[tuple[str, int], ...] = (
    ("gb", 14),
    ("it", 11),
    ("fr", 10),
    ("de", 9),
    ("es", 8),
    ("br", 8),
    ("jp", 7),
    ("nl", 6),
    ("au", 5),
    ("us", 4),
    ("fi", 3),
    ("mx", 3),
    ("ca", 2),
    ("dk", 2),
    ("ar", 2),
    ("mc", 1),
    ("ch", 1),
    ("at", 1),
    ("be", 1),
    ("se", 1),
    ("nz", 1),
    ("th", 1),
    ("cn", 1),
)

# Pools of fictional first and last names per nationality.
# Key: ISO code. Value: (male first names, female first names, last names).
# First names are split by gender; surnames are shared between genders.
DRIVER_NAMES: dict[str, tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]] = {
    # Regno Unito
    "gb": (
        ("Oliver", "Callum", "Freddie", "Jack", "Theo", "Rory", "Ewan", "Marcus"),
        ("Amelia", "Isla", "Freya", "Ivy", "Maisie", "Eleanor", "Harriet", "Rosie"),
        (
            "Aldridge",
            "Whitfield",
            "Carrington",
            "Hargreaves",
            "Stanton",
            "Mercer",
            "Holloway",
            "Fairburn",
            "Osborne",
            "Tilbury",
        ),
    ),
    # Italia
    "it": (
        ("Matteo", "Lorenzo", "Andrea", "Giulio", "Tommaso", "Edoardo", "Riccardo", "Filippo"),
        ("Giulia", "Chiara", "Sofia", "Martina", "Alessia", "Beatrice", "Francesca", "Elena"),
        (
            "Severgnini",
            "Caldara",
            "Montefiori",
            "Bresciani",
            "Vannucci",
            "Lucarelli",
            "Sartorelli",
            "Pellizzari",
            "Comencini",
            "Tarquinio",
        ),
    ),
    # Francia
    "fr": (
        ("Hugo", "Antoine", "Baptiste", "Romain", "Clement", "Maxime", "Julien", "Florent"),
        ("Camille", "Manon", "Chloe", "Lea", "Juliette", "Amelie", "Margaux", "Eloise"),
        (
            "Lemaire",
            "Chevallier",
            "Bordas",
            "Roussel",
            "Marchand",
            "Delacroix",
            "Pelletier",
            "Garnier",
            "Toussaint",
            "Bellanger",
        ),
    ),
    # Germania
    "de": (
        ("Lukas", "Jonas", "Felix", "Maximilian", "Til", "Moritz", "Erik", "Paul"),
        ("Lena", "Hanna", "Mia", "Lea", "Greta", "Johanna", "Annika", "Frieda"),
        (
            "Brandt",
            "Keller",
            "Lindemann",
            "Schreiber",
            "Hofmann",
            "Wegener",
            "Kranz",
            "Steinbach",
            "Vogel",
            "Reuter",
        ),
    ),
    # Spagna
    "es": (
        ("Alvaro", "Pablo", "Iker", "Diego", "Javier", "Marcos", "Adrian", "Raul"),
        ("Lucia", "Marta", "Carmen", "Sara", "Elena", "Paula", "Alba", "Irene"),
        (
            "Ibarra",
            "Cantero",
            "Olmedo",
            "Reyes",
            "Salgado",
            "Vidal",
            "Carrasco",
            "Belmonte",
            "Zubiri",
            "Fuentes",
        ),
    ),
    # Brasile
    "br": (
        ("Thiago", "Rafael", "Gustavo", "Caio", "Bruno", "Enzo", "Pedro", "Vinicius"),
        ("Larissa", "Camila", "Beatriz", "Mariana", "Juliana", "Gabriela", "Leticia", "Fernanda"),
        (
            "Camargo",
            "Andrade",
            "Furtado",
            "Sales",
            "Bittencourt",
            "Rezende",
            "Tavares",
            "Queiroz",
            "Moraes",
            "Pacheco",
        ),
    ),
    # Giappone
    "jp": (
        ("Ren", "Sora", "Daiki", "Haruto", "Kaito", "Yuto", "Riku", "Sho"),
        ("Yui", "Hana", "Aoi", "Rin", "Mei", "Saki", "Akari", "Nanami"),
        (
            "Katsuragi",
            "Imamura",
            "Sakaki",
            "Fujiwara",
            "Takamine",
            "Onoda",
            "Shirakawa",
            "Matsubara",
            "Iwasaki",
            "Kurogane",
        ),
    ),
    # Paesi Bassi
    "nl": (
        ("Daan", "Sven", "Joris", "Thijs", "Lars", "Niek", "Ruben", "Maarten"),
        ("Sanne", "Lotte", "Femke", "Anouk", "Saar", "Fleur", "Eva", "Lieke"),
        (
            "Verhoeven",
            "De Lange",
            "Brouwers",
            "Van Daalen",
            "Kuipers",
            "Smeets",
            "Roosendaal",
            "Terpstra",
            "Vink",
            "Heemskerk",
        ),
    ),
    # Australia
    "au": (
        ("Liam", "Cooper", "Flynn", "Lachlan", "Hayden", "Jed", "Toby", "Mitchell"),
        ("Chloe", "Ruby", "Mia", "Ella", "Zoe", "Tahlia", "Sienna", "Imogen"),
        (
            "Calloway",
            "Brightman",
            "Sutherland",
            "Marsden",
            "Tully",
            "Whitlock",
            "Donovan",
            "Pemberton",
            "Radford",
            "Kearney",
        ),
    ),
    # Stati Uniti
    "us": (
        ("Tyler", "Austin", "Brody", "Chase", "Logan", "Wyatt", "Carter", "Mason"),
        ("Madison", "Hailey", "Brooke", "Savannah", "Paige", "Sydney", "Harper", "Peyton"),
        (
            "Decker",
            "Maxfield",
            "Calhoun",
            "Whitaker",
            "Brennan",
            "Stoddard",
            "Lawson",
            "Pruitt",
            "Hendricks",
            "Garrett",
        ),
    ),
    # Finlandia
    "fi": (
        ("Eero", "Aleksi", "Juho", "Onni", "Veeti", "Tuomas", "Niilo", "Sampo"),
        ("Aada", "Emilia", "Venla", "Saana", "Helmi", "Iida", "Sofia", "Pinja"),
        (
            "Lehtinen",
            "Kallio",
            "Sariola",
            "Niskanen",
            "Hakola",
            "Rantala",
            "Pesonen",
            "Koivisto",
            "Saarela",
            "Tuominen",
        ),
    ),
    # Messico
    "mx": (
        ("Diego", "Santiago", "Emiliano", "Luis", "Mateo", "Andres", "Rodrigo", "Ivan"),
        ("Valeria", "Ximena", "Renata", "Camila", "Daniela", "Regina", "Fernanda", "Andrea"),
        (
            "Cervantes",
            "Olivares",
            "Quintana",
            "Barragan",
            "Esquivel",
            "Zaragoza",
            "Villalobos",
            "Cardenas",
            "Trevino",
            "Arellano",
        ),
    ),
    # Canada
    "ca": (
        ("Ethan", "Noah", "Owen", "Tristan", "Caleb", "Declan", "Nolan", "Brett"),
        ("Emma", "Olivia", "Chloe", "Maeve", "Brielle", "Camille", "Hailey", "Sienna"),
        (
            "Lachapelle",
            "Tremblay",
            "McAllister",
            "Boucher",
            "Sinclair",
            "Gagnon",
            "Wheeler",
            "Beaudry",
            "Falkner",
            "Mercier",
        ),
    ),
    # Danimarca
    "dk": (
        ("Magnus", "Frederik", "Emil", "Oskar", "Anders", "Rasmus", "Viggo", "Soren"),
        ("Freja", "Clara", "Ida", "Alma", "Josefine", "Sofie", "Maja", "Liva"),
        (
            "Dahlgaard",
            "Norgaard",
            "Kristoffersen",
            "Bjerre",
            "Holmgaard",
            "Ostergaard",
            "Brandstrup",
            "Vinther",
            "Skov",
            "Juhl",
        ),
    ),
    # Argentina
    "ar": (
        ("Joaquin", "Nicolas", "Bautista", "Lautaro", "Gonzalo", "Ramiro", "Facundo", "Tomas"),
        ("Martina", "Valentina", "Catalina", "Morena", "Julieta", "Delfina", "Renata", "Pilar"),
        (
            "Echeverria",
            "Almada",
            "Ferreyra",
            "Bustos",
            "Sarmiento",
            "Aguirre",
            "Villagra",
            "Pereyra",
            "Ocampo",
            "Iturbe",
        ),
    ),
    # Monaco
    "mc": (
        ("Leo", "Adrien", "Mathis", "Florian", "Damien", "Cedric"),
        ("Lea", "Camille", "Chloe", "Manon", "Juliette", "Margaux"),
        ("Bartoli", "Lorenzi", "Castellan", "Marchetti", "Renaudin", "Falco"),
    ),
    # Svizzera
    "ch": (
        ("Luca", "Nino", "Fabian", "Joel", "Silvan", "Remo"),
        ("Lara", "Mia", "Elena", "Sofia", "Nina", "Alessia"),
        ("Brunner", "Scharer", "Wenger", "Bissig", "Cavelti", "Hofstetter", "Zollinger", "Marini"),
    ),
    # Austria
    "at": (
        ("Tobias", "Florian", "Simon", "Matthias", "Leon", "Patrick"),
        ("Lena", "Anna", "Marie", "Lea", "Sophie", "Valentina"),
        ("Pichler", "Aigner", "Grasser", "Leitner", "Hofbauer", "Wallner", "Ebner", "Reisinger"),
    ),
    # Belgio
    "be": (
        ("Arthur", "Louis", "Nathan", "Thomas", "Wout", "Gilles"),
        ("Marie", "Emma", "Louise", "Juliette", "Fien", "Noor"),
        (
            "Vandenberghe",
            "Lambrechts",
            "Goossens",
            "Mertens",
            "Declercq",
            "Verbruggen",
            "Peeters",
            "Janssens",
        ),
    ),
    # Svezia
    "se": (
        ("Axel", "Viktor", "Elias", "Hampus", "Nils", "Joel"),
        ("Alva", "Ebba", "Wilma", "Saga", "Astrid", "Elsa"),
        (
            "Lindgren",
            "Akesson",
            "Bergstrom",
            "Nyqvist",
            "Sandell",
            "Holmberg",
            "Eklund",
            "Forsberg",
        ),
    ),
    # Nuova Zelanda
    "nz": (
        ("Finn", "Ryan", "Marcus", "Blake", "Jamie", "Connor"),
        ("Charlotte", "Ruby", "Olivia", "Maia", "Isla", "Aria"),
        ("Hartfield", "Whitmore", "Gallagher", "Penrose", "Aldous", "Kerrigan", "Mackie", "Tane"),
    ),
    # Thailandia
    "th": (
        ("Anan", "Krit", "Tanat", "Phum", "Decha", "Niran"),
        ("Ploy", "Mali", "Suda", "Kanya", "Pim", "Lalita"),
        ("Srisawat", "Chaiyasit", "Wattana", "Phromsuwan", "Kittikorn", "Suwannarat"),
    ),
    # Cina
    "cn": (
        ("Wei", "Hao", "Jun", "Cheng", "Bo", "Kai"),
        ("Lan", "Jing", "Xia", "Ling", "Yan", "Hua"),
        ("Liang", "Zhao", "Sun", "Xu", "Feng", "Qiao", "Deng", "Bai"),
    ),
}


def first_name_pool(nationality: str, gender: str) -> tuple[str, ...]:
    """Il pool di nomi propri per nazionalita' e genere (i cognomi sono a parte)."""
    male_first_names, female_first_names, _ = DRIVER_NAMES[nationality]
    return female_first_names if gender == GENDER_FEMALE else male_first_names


def surname_pool(nationality: str) -> tuple[str, ...]:
    """Il pool di cognomi per nazionalita', condiviso fra i generi."""
    return DRIVER_NAMES[nationality][2]


# Fictional names for the AI teams: generation samples 10 without
# repetition. There must be at least as many as the configured AI teams.
TEAM_NAMES: tuple[str, ...] = (
    "Aurora Grand Prix",
    "Vortice Corse",
    "Falco Racing",
    "Meridiana Motorsport",
    "Boreale GP",
    "Cobalto Racing",
    "Vulcania Corse",
    "Scuderia Argento",
    "Kestrel Motorsport",
    "Tempesta Racing",
    "Helios Grand Prix",
    "Drakkar Motorsport",
    "Sagitta Corse",
    "Ponente Racing",
)

# Fictional names for the engine suppliers: generation samples 3-4 without
# repetition. There must be at least as many as the configured maximum.
ENGINE_SUPPLIER_NAMES: tuple[str, ...] = (
    "Vulcano Motori",
    "Albion Power Units",
    "Rheinkraft",
    "Sakura Dynamics",
    "Itaca Propulsione",
    "Atlantica Engines",
)
