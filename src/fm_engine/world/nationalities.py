"""Dati anagrafici per la generazione del Mondo: nazionalita' e pool di nomi.

Le nazionalita' sono codici ISO 3166-1 alpha-2 minuscoli (forma canonica
del progetto, coerente con la colonna drivers.nationality dello schema DB):
la TUI ne deriva la bandiera, NATION_NAMES fornisce il nome leggibile.

I pesi delle nazionalita' riflettono i vivai reali del motorsport (Regno
Unito, Italia, Francia, Germania, Spagna, Brasile, Giappone, Paesi Bassi,
Australia, piu' code lunghe). Sono parametri di partenza tarabili: la
WorldConfig li espone come default sovrascrivibile.

Tutti i nomi sono di fantasia. A valle restano semplici stringhe editabili
via DB (Studio), come da convenzione di FOR-3.
"""

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
# Key: ISO code. Value: (first names, last names).
DRIVER_NAMES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    # Regno Unito
    "gb": (
        ("Oliver", "Callum", "Freddie", "Jack", "Theo", "Rory", "Ewan", "Marcus"),
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
        ("Bartoli", "Lorenzi", "Castellan", "Marchetti", "Renaudin", "Falco"),
    ),
    # Svizzera
    "ch": (
        ("Luca", "Nino", "Fabian", "Joel", "Silvan", "Remo"),
        ("Brunner", "Scharer", "Wenger", "Bissig", "Cavelti", "Hofstetter", "Zollinger", "Marini"),
    ),
    # Austria
    "at": (
        ("Tobias", "Florian", "Simon", "Matthias", "Leon", "Patrick"),
        ("Pichler", "Aigner", "Grasser", "Leitner", "Hofbauer", "Wallner", "Ebner", "Reisinger"),
    ),
    # Belgio
    "be": (
        ("Arthur", "Louis", "Nathan", "Thomas", "Wout", "Gilles"),
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
        ("Hartfield", "Whitmore", "Gallagher", "Penrose", "Aldous", "Kerrigan", "Mackie", "Tane"),
    ),
    # Thailandia
    "th": (
        ("Anan", "Krit", "Tanat", "Phum", "Decha", "Niran"),
        ("Srisawat", "Chaiyasit", "Wattana", "Phromsuwan", "Kittikorn", "Suwannarat"),
    ),
    # Cina
    "cn": (
        ("Wei", "Hao", "Jun", "Cheng", "Bo", "Kai"),
        ("Liang", "Zhao", "Sun", "Xu", "Feng", "Qiao", "Deng", "Bai"),
    ),
}

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
