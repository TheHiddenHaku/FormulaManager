"""Libreria dei template di Telecronaca (FOR-16, ADR 0003).

Ogni tipo di evento del motore ha una famiglia di frasi parametriche in
italiano, tono da cronaca radiofonica. I segnaposto fra graffe sono
riempiti dai costruttori di parametri in narrator.py; ogni famiglia ha
piu' varianti di REPETITION_WINDOW cosi' la selezione anti-ripetizione
trova sempre una variante libera.
"""

from fm_engine import events

# Template families keyed by event type. Every variant of a family must
# use the same placeholder set produced by its parameter builder.
TEMPLATES: dict[type, tuple[str, ...]] = {
    events.RaceStarted: (
        "Semaforo verde! Si parte a {circuit}: {total_laps} giri ci separano dalla bandiera"
        " a scacchi!",
        "Si spengono i semafori e la gara di {circuit} e' cominciata: {total_laps} giri tutti"
        " da vivere!",
        "Via! Il gruppo si lancia verso la prima curva di {circuit}, {total_laps} giri davanti"
        " a noi!",
        "Partiti! Rombo di motori a {circuit}: comincia una gara di {total_laps} giri!",
        "E si parte! {circuit} si accende: {total_laps} giri per scrivere la storia di questo"
        " Gran Premio!",
        "Luci spente, gara al via a {circuit}! Davanti a noi {total_laps} giri di battaglia!",
    ),
    events.Overtake: (
        "Sorpasso! {driver} infila {overtaken} e sale in posizione {position}!",
        "Che manovra di {driver}! {overtaken} non puo' nulla: posizione {position}!",
        "{driver} trova il varco su {overtaken} e si prende la posizione {position}!",
        "Attacco riuscito! {driver} supera {overtaken} al giro {lap} ed e' ora in posizione"
        " {position}!",
        "Staccata profonda di {driver}! {overtaken} deve cedere la posizione {position}!",
        "Duello vinto da {driver}: {overtaken} si arrende, la posizione {position} cambia padrone!",
    ),
    events.TeamOrderSwap: (
        "Ordine di scuderia in casa {team}: {promoted} passa davanti a {demoted} per la"
        " posizione {position}.",
        "Dal muretto {team} arriva l'ordine: {promoted} davanti, {demoted} si fa da parte in"
        " posizione {position}.",
        "Giochi di squadra in {team}: {demoted} lascia strada a {promoted}, che sale in"
        " posizione {position}.",
        "Il muretto {team} ha deciso: {promoted} scavalca {demoted} e prende la posizione"
        " {position}.",
        "Scambio ordinato in casa {team}: {promoted} ringrazia {demoted} e si porta in"
        " posizione {position}.",
        "Niente duello tra compagni: {team} congela la sfida, {promoted} davanti a {demoted}"
        " in posizione {position}.",
    ),
    events.FastestLap: (
        "Giro veloce! {driver} ferma il cronometro su {time}!",
        "Tempone di {driver}: {time}, e' il nuovo giro piu' veloce della gara!",
        "{driver} vola: {time} e giro veloce strappato al giro {lap}!",
        "Cronometro viola per {driver}: {time}, nessuno ha fatto meglio finora!",
        "Che passo di {driver}! Il giro veloce e' suo: {time}!",
        "{driver} alza il ritmo e firma il miglior giro: {time}!",
    ),
    events.CarFailure: (
        "Guasto per {driver}! Cede {component}, che sfortuna al giro {lap}!",
        "Problema tecnico sulla vettura di {driver}: {component} non risponde piu'!",
        "Fumo dalla monoposto di {driver}: e' {component} che ha ceduto!",
        "Che botta per {driver}: {component} alza bandiera bianca al giro {lap}!",
        "Affidabilita' tradita per {driver}: {component} ha detto basta!",
        "Disastro tecnico per {driver}: cede di schianto {component}!",
    ),
    events.DriverError: (
        "Errore di {driver}: {cause} e {time_lost} secondi persi!",
        "Sbavatura di {driver}: {cause}, se ne vanno {time_lost} secondi.",
        "{driver} perde {time_lost} secondi: {cause} al giro {lap}!",
        "Brivido per {driver}! Colpa di {cause}: {time_lost} secondi buttati via.",
        "Attimo di panico per {driver}: {cause}, {time_lost} secondi che pesano.",
        "{driver} non e' perfetto stavolta: {cause}, {time_lost} secondi lasciati in pista.",
    ),
    events.Accident: (
        "Bandiere gialle: {severity_phrase} coinvolge {drivers} al giro {lap}!",
        "Caos in pista, {severity_phrase} per {drivers}!",
        "Attenzione: {severity_phrase} al giro {lap}, coinvolti {drivers}!",
        "Succede di tutto: {severity_phrase} mette nei guai {drivers}!",
        "Che botto al giro {lap}: {severity_phrase} con protagonisti {drivers}!",
        "Sportellate in pista: {severity_phrase} tra {drivers}!",
    ),
    events.CarDamage: (
        "Danni sulla vettura di {driver}: il conto per la squadra sale di {amount}.",
        "Carbonio in pista per {driver}: riparazioni stimate in {amount}.",
        "La monoposto di {driver} e' ammaccata: danni per {amount}.",
        "Brutte notizie per i meccanici di {driver}: danni quantificati in {amount}.",
        "Il muretto fa i conti: {amount} di danni sulla vettura di {driver}.",
        "Vettura ferita per {driver}: il danno vale {amount}.",
    ),
    events.Dnf: (
        "Ritiro! La gara di {driver} finisce qui al giro {lap}: fatale {cause}.",
        "Game over per {driver}: {cause} lo costringe al ritiro.",
        "Si chiude in anticipo la domenica di {driver}: {cause} al giro {lap}.",
        "Abbandono per {driver}! La causa: {cause}.",
        "{driver} parcheggia la monoposto: {cause} pone fine alla sua gara.",
        "Niente da fare per {driver}: {cause} e gara finita al giro {lap}.",
    ),
    events.SafetyCarDeployed: (
        "Safety car! La vettura di sicurezza entra in pista al giro {lap}!",
        "Ecco la safety car: gruppo compattato e distacchi azzerati!",
        "Neutralizzazione! La safety car guida il gruppo dal giro {lap}.",
        "Safety car in pista: occasione ghiotta per un pit stop a prezzo di saldo!",
        "Regime di safety car: tutti in fila indiana dietro la vettura di sicurezza.",
        "La direzione gara chiama la safety car: la corsa si congela al giro {lap}.",
    ),
    events.SafetyCarEnding: (
        "La safety car rientra! Si riparte al giro {lap}: occhi aperti alla ripartenza!",
        "Luci spente sulla safety car: tra poco si torna a correre!",
        "Safety car ai box! Ripartenza lanciata, puo' succedere di tutto!",
        "Fine della neutralizzazione: il gruppo si rilancia al giro {lap}!",
        "Si riparte! La safety car lascia la pista e la bagarre puo' ricominciare!",
        "Ripartenza! Safety car dentro e gas spalancato per tutti!",
    ),
    events.VscDeployed: (
        "Virtual safety car al giro {lap}: tutti a velocita' ridotta!",
        "Regime di VSC: distacchi congelati su tutto il tracciato.",
        "Scatta la virtual safety car: delta da rispettare per tutti i piloti.",
        "VSC in vigore dal giro {lap}: la corsa rallenta ma non si ferma.",
        "Bandiere gialle e VSC: il cronometro detta il passo a tutto il gruppo.",
        "Virtual safety car! Chi rischia il pit stop adesso paga meta' prezzo.",
    ),
    events.VscEnding: (
        "Fine del VSC al giro {lap}: si torna a spingere!",
        "VSC concluso: pista verde e gara di nuovo lanciata!",
        "Termina la virtual safety car: tutti di nuovo a tutta!",
        "Verde! Il VSC si spegne al giro {lap} e la corsa riparte.",
        "Via il VSC: i piloti possono riaprire il gas!",
        "La virtual safety car saluta: ritmo di gara di nuovo libero!",
    ),
    events.RainStarted: (
        "Inizia a piovere! Pioggia {intensity} sul circuito dal giro {lap}!",
        "Gocce sulla pista: arriva una pioggia {intensity}!",
        "Si apre il cielo: pioggia {intensity}, i muretti studiano le mosse!",
        "Pioggia {intensity} in arrivo al giro {lap}: la pista cambia faccia!",
        "Ecco l'acqua! Pioggia {intensity}: la gara si complica!",
        "Meteo protagonista: pioggia {intensity} sul tracciato!",
    ),
    events.RainStopped: (
        "Smette di piovere al giro {lap}: la pista comincia ad asciugarsi!",
        "Stop alla pioggia: torna a filtrare un po' di luce sul circuito!",
        "La pioggia ci ripensa: pista in via di asciugatura!",
        "Cessa la pioggia al giro {lap}: traiettoria asciutta in costruzione!",
        "Fine dell'acquazzone: ora la pista migliora giro dopo giro!",
        "Niente piu' pioggia: i piloti cercano l'asciutto a ogni curva!",
    ),
    events.Crossover: (
        "Crossover! Le gomme {to_category} sono ora la scelta giusta!",
        "Cambio di scenario al giro {lap}: conviene passare alle gomme {to_category}!",
        "Il cronometro parla chiaro: e' il momento delle gomme {to_category}!",
        "Le gomme {from_category} hanno fatto il loro tempo: ora volano le gomme {to_category}!",
        "Finestra di crossover aperta al giro {lap}: dalle gomme {from_category} alle gomme"
        " {to_category}!",
        "Strategia in fibrillazione: chi monta le gomme {to_category} adesso ci guadagna!",
    ),
    events.UndercutWindow: (
        "Finestra di undercut! {driver} puo' attaccare {target} fermandosi ai box adesso!",
        "Strategia in gioco al giro {lap}: {driver} ha l'undercut su {target}, distacco di"
        " {gap} secondi!",
        "Occhio ai muretti: {driver} e' in finestra di undercut su {target}!",
        "Le gomme di {target} calano: una sosta immediata puo' regalare la posizione a {driver}!",
        "{gap} secondi tra {target} e {driver}: chi anticipa la sosta puo' ribaltare il duello!",
        "Si apre l'undercut al giro {lap}: {driver} ha {target} a tiro di pit stop!",
    ),
    events.PitEntry: (
        "{driver} ai box! Rientra al giro {lap}!",
        "Eccolo: {driver} imbocca la corsia dei box!",
        "Pit stop per {driver}: i meccanici sono pronti!",
        "{driver} rompe gli indugi e si tuffa ai box al giro {lap}!",
        "Mossa ai box: {driver} rientra per la sosta!",
        "La squadra chiama, {driver} risponde: e' ai box!",
    ),
    events.TyreChange: (
        "Cambio gomme per {driver}: via le gomme {old_compound}, dentro le gomme {new_compound}!",
        "{driver} passa dalle gomme {old_compound} alle gomme {new_compound}!",
        "Set fresco per {driver}: montate le gomme {new_compound}!",
        "I meccanici scatenati: {driver} lascia le gomme {old_compound} e riparte con le gomme"
        " {new_compound}!",
        "Sosta per {driver}: la scelta cade sulle gomme {new_compound}!",
        "Treno nuovo per {driver}: ora e' su gomme {new_compound}!",
    ),
    events.PitExit: (
        "{driver} torna in pista: sosta da {time_lost} secondi complessivi!",
        "Pit stop completato: {driver} riparte dopo {time_lost} secondi persi!",
        "Rientro in gara per {driver}: il passaggio ai box e' costato {time_lost} secondi.",
        "{driver} riprende la corsa: {time_lost} secondi lasciati in corsia box.",
        "Fine della sosta: {driver} di nuovo in battaglia, {time_lost} secondi il conto totale.",
        "Semaforo verde in corsia: {driver} torna in pista, sosta da {time_lost} secondi.",
    ),
    events.BiCompoundPenalty: (
        "Penalita' per {driver}: {penalty} secondi per non aver usato due mescole!",
        "La direzione gara punisce {driver}: {penalty} secondi aggiunti per l'obbligo di"
        " doppia mescola violato.",
        "{driver} paga la strategia a mescola unica: {penalty} secondi di penalita'!",
        "Sanzione in arrivo: {penalty} secondi sul tempo di {driver} per il regolamento gomme.",
        "Niente seconda mescola per {driver}: {penalty} secondi di penalita' in classifica.",
        "Il regolamento presenta il conto a {driver}: {penalty} secondi di penalita'!",
    ),
    events.OrderConfirmed: (
        "Via radio a {driver}: {order}. Messaggio ricevuto.",
        "Il muretto chiama {driver}: la consegna e' {order}.",
        "Nuovo ordine per {driver}: {order}. Copiato.",
        "Comunicazione di squadra per {driver}: {order}.",
        "{driver} conferma via radio: {order}.",
        "Dal box arriva l'ordine a {driver}: {order}.",
    ),
    events.ChequeredFlag: (
        "Bandiera a scacchi! Vince {winner}! Che gara!",
        "E' finita! Trionfo di {winner} sotto la bandiera a scacchi!",
        "{winner} taglia il traguardo per primo: vittoria!",
        "Bandiera a scacchi al giro {lap}: il successo e' di {winner}!",
        "Vittoria di {winner}! Il suo muretto esplode di gioia!",
        "Si chiude qui: {winner} vince e convince!",
    ),
    events.QualifyingTimeSet: (
        "{driver} ferma il cronometro su {time} in {segment}!",
        "Bel giro di {driver}: {time} sul tabellone della {segment}!",
        "{driver} si migliora: {time} e' il suo riferimento in {segment}.",
        "Tempo di rilievo in {segment}: {driver} stampa un {time}!",
        "La pista parla: {driver} firma {time} in {segment}.",
        "Giro pulito di {driver}: {time} in {segment}.",
    ),
    events.QualifyingElimination: (
        "Eliminato! {driver} si ferma in {segment}: scattera' dalla casella {position}.",
        "Niente da fare per {driver}: fuori in {segment}, griglia numero {position}.",
        "{driver} non passa il taglio della {segment}: per lui posizione {position} in griglia.",
        "Si chiude in {segment} la qualifica di {driver}: partira' dalla posizione {position}.",
        "Beffa per {driver}: eliminato in {segment}, casella {position} sulla griglia.",
        "Il cronometro condanna {driver}: fuori in {segment}, posizione di partenza numero"
        " {position}.",
    ),
    events.PolePosition: (
        "Pole position! {driver} si prende la prima casella con {time}!",
        "Pole per {driver}! Giro da urlo: {time}!",
        "Nessuno come {driver}: pole position in {time}!",
        "La prima fila parla chiaro: {driver} in pole con {time}!",
        "Urlo di gioia dal box: {driver} firma la pole in {time}!",
        "{driver} domina le qualifiche: pole position e {time} sul cronometro!",
    ),
}
