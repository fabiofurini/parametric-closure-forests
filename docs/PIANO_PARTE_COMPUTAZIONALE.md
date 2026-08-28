# Piano per la parte computazionale del nuovo paper sulla closure parametrica

## Stato del documento

Questo documento è stato validato come direzione di lavoro; l'implementazione del
nucleo C++ è in corso. Non modifica il manoscritto e non autorizza ancora
l'esecuzione della campagna computazionale completa.

Principi già stabiliti:

1. Il vecchio codice, i vecchi repository GitHub, gli archivi di istanze, i CSV e
   il paper arXiv restano invariati e costituiscono una pubblicazione storica.
2. Il nuovo progetto computazionale deve essere autonomo: nuova directory, nuovo
   repository Git, nuova documentazione, nuovi test, nuove istanze e nuovi risultati.
3. È ammesso trasferire algoritmi matematicamente coincidenti dal vecchio codice,
   ma soltanto mediante un porting esplicito, tracciato e verificato. Il nuovo
   progetto non deve compilare, importare o leggere file dal vecchio progetto.
4. Il nuovo linguaggio scientifico è quello della **parametric closure**. Non devono
   comparire capacità, soluzione di knapsack, split item, LP del PCKP o terminologia
   dipendente dal KP.
5. La parte Rake-and-Compress (RaC) va recuperata dai materiali sperimentali
   disponibili, sottoposta ad audit e poi integrata come codice del nuovo progetto.
6. L'unico manoscritto che verrà modificato è la **versione v2 del nuovo paper**.
   La versione arXiv/v1 e i relativi sorgenti restano congelati.
7. Il nuovo codice e le nuove istanze closure-specifiche, ereditate e “rivestite”
   a partire dal materiale storico, saranno pubblicati in un **nuovo GitHub
   completamente indipendente e autosufficiente**.
8. Il nuovo GitHub conterrà il codice effettivamente usato per tutti gli esperimenti,
   compreso il nuovo algoritmo RaC, e tutto ciò che serve per compilare, validare,
   generare le istanze, eseguire i benchmark e riprodurre tabelle e figure.

---

## 1. Obiettivo scientifico della nuova infrastruttura

L'infrastruttura deve calcolare e confrontare algoritmi per il seguente problema.
Dato un grafo diretto di precedenze `G=(V,A)` e, per ogni nodo `i`, una funzione
affine

```text
c_i(lambda) = p_i - lambda * w_i,
```

si vuole determinare, al variare di `lambda`, una famiglia canonica e annidata di
closure ottime, tutti i breakpoint e la corrispondente sequenza di differenze tra
closure consecutive (macroitems, secondo la terminologia del paper).

Assunzioni iniziali proposte:

- `p_i` è intero con segno;
- `w_i` è intero strettamente positivo;
- un arco `(u,v)` significa `u in X => v in X`;
- il grafo non orientato sottostante è una foresta;
- le orientazioni degli archi possono essere arbitrarie;
- breakpoint e confronti tra rapporti devono essere esatti.

Queste assunzioni devono essere confrontate con le ipotesi definitive dei teoremi
prima di congelare il formato delle istanze.

### Output canonico richiesto

Per ogni istanza, ogni algoritmo deve restituire lo stesso oggetto logico:

- sequenza ordinata dei breakpoint razionali;
- partizione ordinata dei nodi in macroitems;
- closure cumulativa associata a ciascun intervallo di `lambda`;
- checksum canonico della sequenza;
- statistiche dell'algoritmo;
- tempo e memoria, misurati separatamente dalle operazioni di input/output e dai
  controlli di correttezza.

Breakpoint uguali devono essere gestiti da una regola canonica unica: in assenza di
una diversa scelta teorica, si propone di unire macroitems consecutivi con lo stesso
rapporto esatto.

---

## 2. Separazione netta dal progetto arXiv precedente

L'obiettivo editoriale è produrre **due paper indipendenti**, con domande scientifiche
diverse:

1. **Paper teorico sulla rilassata LP del PCKP.** Studia la struttura delle soluzioni
   LP, la sequenza ottima di macroitems e le conseguenze primali/duali nel contesto
   del precedence-constrained knapsack. A questo lavoro appartengono la versione
   arXiv/v1 e, fino a decisione successiva, i materiali GitHub storici.
2. **Paper sulla parametric closure nelle foreste orientate.** Studia il problema
   parametrico direttamente nel mondo della closure, gli algoritmi FMA/HFMA e le
   varianti specializzate, il nuovo algoritmo RaC e il loro comportamento
   computazionale. A questo lavoro appartengono la versione v2, il nuovo codice, le
   istanze closure-specifiche rivestite e il nuovo GitHub autosufficiente.

I due paper non devono dipendere l'uno dall'altro per compilazione, verifica o
riproduzione degli esperimenti. Il paper sulla parametric closure non deve essere
presentato come una nuova versione del paper LP/PCKP, ma come un contributo distinto
con formulazione, codice, istanze, risultati e repository propri.

Qualsiasi decisione futura sullo stato, aggiornamento, archiviazione o presentazione
dei vecchi GitHub e del vecchio paper arXiv è esplicitamente rinviata e resta fuori
dallo scope del presente piano.

### 2.1 Directory proposta

Dopo l'approvazione del piano il progetto computazionale risiede nella cartella del
nuovo paper:

```text
Parametric_Closure/COMPUTATIONAL/
```

Questa directory non è una sottocartella di `CODE_FOREST` o `GITHUB`. Sarà la radice
del nuovo repository Git indipendente quando il contenuto verrà pubblicato.

Nome provvisorio del futuro repository pubblico:

```text
parametric-closure-forests
```

Il nome definitivo è una decisione aperta.

### 2.2 Materiale legacy da considerare read-only

Le seguenti aree non devono essere modificate o usate come dipendenze runtime:

```text
PAPER/
CODE_FOREST/
CODE_PARAMETRIC_PSEUDOFLOW/
GITHUB/
```

In particolare, non deve essere eseguito `GITHUB/deploy_to_github.sh`.

### 2.3 Regola per il riuso

Il riuso deve avvenire in tre passi:

1. identificazione della componente matematica riusabile;
2. copia una tantum nel nuovo progetto, con nota di provenienza;
3. revisione di nomi, interfacce, test e dipendenze per renderla nativa al problema
   di closure parametrica.

Il nuovo progetto dovrà compilare e superare i test anche se tutte le cartelle
legacy vengono temporaneamente rese non disponibili.

---

## 3. Componenti riusabili e componenti da eliminare

| Componente legacy | Decisione proposta | Motivazione |
|---|---|---|
| Confronto esatto tra rapporti | Portare e rafforzare | Serve direttamente per i breakpoint razionali. |
| Validazione di foresta/in-forest/out-forest | Portare, rinominare e testare | È indipendente dal KP. |
| FMA su foreste orientate | Portare | È uno degli algoritmi del nuovo paper. |
| DFMA su foreste orientate | Portare | È la variante duale generale di FMA. |
| HFMA su foreste orientate | Portare | È il principale algoritmo pratico di confronto. |
| DHFMA su foreste orientate | Portare | È la variante duale heap-based generale di HFMA. |
| HIMA/HOMA | Portare nel core; decidere se includerli negli esperimenti | Sono le varianti heap specializzate, rispettivamente primale per in-forest e duale per out-forest. |
| Parser del vecchio formato | Non portare direttamente | Usa `profits` e `weights` e porta con sé semantica legacy. |
| `solution.cpp` e split macroitem | Escludere | Dipendono dalla capacità e dalla soluzione del PCKP. |
| `pckp_lp.cpp` | Escludere | Non appartiene al nuovo problema. |
| `lp_highs.cpp` e dipendenza HiGHS | Escludere dal core | Per la closure è preferibile un oracle max-flow indipendente. |
| Dinkelbach legacy | Non portare come algoritmo principale | Era inserito nel flusso PCKP/LP; l'eventuale oracle va riprogettato. |
| Writer di risultati legacy | Riscrivere | Le colonne capacity/objective/split non sono pertinenti. |
| Generatori legacy | Usare come base genealogica, poi riscrivere | Topologie, seed e famiglie statistiche possono essere ereditati, ma formato, terminologia, metadati e motivazione devono diventare closure-specifici. |
| CSV e tempi legacy | Non riutilizzare | Rimangono evidenza del paper arXiv, non del nuovo paper. |
| Adapter BPPF | Riscrivere nel nuovo progetto | BPPF resta un baseline pertinente alla parametric closure. |

Il porting deve includere un file `PROVENANCE.md` che elenchi file di origine,
data del trasferimento, trasformazioni effettuate e test usati per verificare
l'equivalenza. La stessa regola vale per le istanze: il nuovo dataset deve indicare
quali file o famiglie derivano dal test bed storico e quale trasformazione è stata
applicata per ottenere il formato closure-specifico.

---

## 4. Architettura proposta del nuovo repository

```text
Parametric_Closure/COMPUTATIONAL/
├── CMakeLists.txt
├── README.md
├── LICENSE
├── CITATION.cff
├── PROVENANCE.md
├── cmake/
├── include/parametric_closure/
│   ├── instance.hpp
│   ├── rational.hpp
│   ├── sequence.hpp
│   ├── fma.hpp
│   ├── hfma.hpp
│   ├── hima.hpp
│   ├── homa.hpp
│   ├── rac.hpp
│   └── oracle.hpp
├── src/
│   ├── instance.cpp
│   ├── rational.cpp
│   ├── sequence.cpp
│   ├── fma.cpp
│   ├── hfma.cpp
│   ├── hima.cpp
│   ├── homa.cpp
│   ├── rac.cpp
│   ├── oracle_bruteforce.cpp
│   ├── oracle_maxflow.cpp
│   └── cli.cpp
├── tests/
│   ├── unit/
│   ├── differential/
│   ├── exhaustive/
│   ├── regression/
│   └── fixtures/
├── instances/
│   ├── tiny/
│   └── manifests/
├── tools/
│   ├── convert_legacy_instances.cpp
│   ├── generate_instances.cpp
│   ├── benchmark.cpp
│   ├── validate_raw_data.cpp
│   ├── aggregate_results.cpp
│   └── emit_latex_tables.cpp
├── data/
│   ├── raw/
│   ├── processed/
│   └── manifests/
├── results/
│   ├── tables/
│   └── figures/
├── external/
│   └── README.md
└── docs/
    ├── INSTANCE_FORMAT.md
    ├── EXPERIMENTAL_PROTOCOL.md
    ├── REPRODUCIBILITY.md
    └── RAC_AUDIT.md
```

Gli algoritmi, la libreria e gli eseguibili che producono i risultati sperimentali
rimangono in C++.  Python è ammesso esclusivamente per le utility riproducibili:
conversione e controllo dei file, generazione di manifest, aggregazione dei dati,
grafici e tabelle LaTeX. Le utility non devono mai contenere una seconda
implementazione degli algoritmi né determinare i risultati computazionali.

Il nuovo GitHub deve essere il punto unico di accesso al nuovo codice e alle nuove
istanze. I grandi archivi non devono necessariamente essere inseriti nella storia
Git: nel repository vanno generatori, convertitori, manifest, checksum e fixture,
mentre gli archivi completi devono essere allegati alle release dello stesso GitHub
oppure depositati con DOI e collegati stabilmente dal repository.

Una persona che clona il nuovo GitHub non deve aver bisogno del vecchio codice o dei
vecchi repository. Se gli archivi completi sono asset di release, gli script devono
saperli scaricare, verificarne il checksum e svolgere la pipeline senza riferimenti
al workspace storico.

---

## 5. Nuovo formato delle istanze

Si propone un formato testuale versionato e privo di terminologia KP:

```text
pcf 1
n 4
profits 10 -3 8 2
weights 2 1 4 1
arcs 3
1 2
3 2
4 3
```

Semantica:

- `profits` contiene i `p_i`;
- `weights` contiene i `w_i > 0`;
- gli identificativi nei file sono 1-based;
- l'arco `u v` impone `u in X => v in X`;
- nessuna capacità è memorizzata o passata da CLI;
- ogni file contiene una sola istanza;
- commenti e metadati opzionali devono avere una sintassi specificata.

La CLI proposta è:

```text
pcf_solve --instance FILE --algorithm fma|hfma|hima|homa|rac \
          [--output FILE] [--stats FILE] [--verify]
```

`--verify` non deve essere incluso nel tempo dell'algoritmo.

---

## 6. Recupero e audit di RaC

### 6.1 Materiale individuato

Nell'archivio

```text
LLM_PROPOSTE_SEPARAZIONI_PAPERI.tar.gz
```

è presente il pacchetto interno

```text
MACROITEMS_PAPER/LLMs/CONTROPROSTA_DI_CHAT/TESTS_CHAT/
top_tree_cpp_experiment_package.zip
```

che contiene:

- `algo_top_tree.cpp/.hpp`;
- un benchmark C++ HFMA/top-tree;
- generatore di mixed stars;
- runner della campagna;
- CSV raw e aggregati;
- report tecnico;
- una copia del manoscritto sperimentale.

Il pacchetto dichiara:

- 1.600 controlli su piccole istanze;
- 2.655 confronti C++ appaiati senza mismatch;
- test su random, path, binary e mixed star;
- implementazione con confronti razionali esatti e statistiche su cluster/envelope.

Questi risultati sono **materiale preliminare da riprodurre**, non dati già
accettabili per il nuovo paper.

Esiste anche un prototipo Python `fastforest`; il suo stesso report chiarisce che
non implementa una top tree bilanciata. Quel prototipo può essere utile per capire
le formule, ma non deve diventare il codice RaC pubblicato né un baseline temporale.

### 6.2 Audit matematico richiesto

Prima dell'integrazione, `algo_top_tree.cpp` deve essere mappato riga per riga sulle
operazioni del paper:

1. rappresentazione di 1-cluster e 2-cluster;
2. vincolo `|boundary| <= 2`;
3. rappresentazione delle funzioni convesse lineari a tratti;
4. somma di envelope;
5. massimo di envelope;
6. `Compress1`;
7. `Compress2`;
8. `Rake`;
9. scelta dell'insieme indipendente e avanzamento per round;
10. ricostruzione top-down delle soglie dei nodi;
11. estrazione canonica dei macroitems;
12. prova operativa del limite sul numero di round e sulla profondità.

Ogni discrepanza tra pseudocodice e implementazione va documentata in
`docs/RAC_AUDIT.md` e risolta prima dei benchmark ufficiali.

### 6.3 Audit numerico e di robustezza

Il codice recuperato usa interi a 64 bit e prodotti incrociati. Occorre stabilire:

- limiti massimi sicuri di `n`, `p_i` e `w_i`;
- punti in cui è necessario `__int128`;
- normalizzazione dei razionali con denominatore positivo;
- comportamento in presenza di breakpoint coincidenti;
- comportamento con coefficienti negativi;
- gestione esplicita di overflow, anziché overflow silenzioso;
- compatibilità tra risultati RaC, FMA e HFMA sotto la stessa regola canonica.

### 6.4 Gate di accettazione RaC

RaC entra nella campagna ufficiale soltanto se:

- supera tutti i test unitari sulle operazioni di cluster;
- coincide con enumerazione completa su tutte le istanze small;
- coincide con FMA e HFMA sui test differenziali;
- supera sanitizer e controlli overflow;
- il codice corrisponde all'algoritmo descritto nel paper;
- nessun fallback nascosto richiama FMA/HFMA per costruire il risultato.

---

## 7. Strategia di verifica della correttezza

La correttezza non deve basarsi soltanto sul fatto che due implementazioni derivate
dallo stesso vecchio codice coincidano.

### 7.1 Oracle 1: enumerazione completa

Per `n` piccolo si enumerano tutti i sottoinsiemi chiusi, si costruiscono le rette
associate e si calcola esattamente l'envelope superiore. Questo restituisce tutti i
breakpoint e una sequenza canonica indipendente dagli algoritmi del paper.

Uso previsto:

- tutte le fixture fino a una soglia ragionevole (`n <= 20`, da misurare);
- migliaia di istanze casuali fino a `n=10`;
- enumerazione sistematica delle orientazioni per alberi molto piccoli;
- casi con rapporti uguali, coefficienti negativi e componenti multiple.

### 7.2 Oracle 2: maximum closure a lambda fissato

Si implementa un solver max-flow/min-cut indipendente. Per un valore razionale
`lambda=p/q`, i coefficienti vengono trasformati esattamente in

```text
q * p_i - p * w_i.
```

Si verifica l'ottimalità delle closure restituite:

- in ogni intervallo aperto tra breakpoint consecutivi;
- esattamente sui breakpoint, controllando le closure minime e massime;
- prima del primo e dopo l'ultimo breakpoint rilevante.

Questo oracle non richiede capacità, LP del PCKP o HiGHS.

### 7.3 Test differenziali

Per ogni istanza compatibile:

- FMA vs HFMA;
- FMA vs RaC;
- HFMA vs RaC;
- HIMA vs algoritmi generali sulle in-forest;
- HOMA vs algoritmi generali sulle out-forest;
- tutti gli algoritmi vs oracle sulle istanze small.

Il confronto deve includere breakpoint esatti, partizione, ordine canonico e closure
cumulative; non basta confrontare il solo numero di macroitems.

### 7.4 Infrastruttura test

Il nuovo CMake deve usare realmente CTest:

```cmake
include(CTest)
enable_testing()
add_test(...)
```

Configurazioni minime di CI:

- GCC Release;
- GCC Debug con AddressSanitizer e UndefinedBehaviorSanitizer;
- Clang Debug;
- test C++ dei generatori, dei converter e degli strumenti di analisi;
- smoke benchmark non prestazionale.

---

## 8. Nuove famiglie di istanze

Le istanze ufficiali del nuovo paper saranno **ereditate e rivestite** a partire dal
test bed storico, senza modificare gli archivi legacy. La migrazione deve essere
riproducibile, verificabile e inclusa nel nuovo GitHub; non può consistere in una
copia manuale o in una semplice rinomina.

La corrispondenza semantica iniziale proposta è:

```text
legacy profit p_i  -> profit p_i
legacy weight w_i  -> weight w_i
legacy arc (u,v)   -> closure implication u in X => v in X
```

La capacità non faceva parte dei file di istanza e non entra nella migrazione. Il
nuovo file `.pcf` contiene soltanto grafo e coefficienti affini.

Un convertitore versionato nel nuovo repository deve:

1. leggere il formato storico;
2. validare grafo e coefficienti;
3. produrre il formato `.pcf` closure-specifico;
4. registrare nel manifest il checksum del sorgente e della destinazione;
5. dimostrare che grafo e valori numerici sono preservati;
6. non richiedere il vecchio repository durante la riproduzione pubblica: gli input
   necessari alla conversione devono essere inclusi come asset della nuova release,
   oppure le istanze già convertite devono essere distribuite direttamente.

Quando il generatore storico è disponibile, è ammessa una rigenerazione compatibile
con gli stessi parametri e seed, purché l'equivalenza sia controllata tramite
checksum o confronto strutturale completo.

Le istanze strutturate necessarie a RaC — path, binary e mixed star — vengono
recuperate dai materiali RaC, rigenerate nel nuovo formato e distribuite nello stesso
nuovo GitHub insieme ai generatori.

### 8.1 Topologie random

1. `mixed-forest`: foresta non orientata casuale, ogni arco orientato
   indipendentemente;
2. `mixed-tree`: caso connesso della famiglia precedente;
3. `in-forest`: out-degree al più uno;
4. `out-forest`: in-degree al più uno.

Per le foreste casuali si può mantenere il parametro strutturale

```text
rho in {0.3, 0.6, 0.9, 1.0},
```

ma va presentato come probabilità di collegamento/densità della foresta, senza
riferimenti alle istanze KP.

### 8.2 Topologie strutturate per RaC

1. `path-mixed`;
2. `binary-mixed` (albero binario bilanciato, con ultimo livello eventualmente
   incompleto);
3. `star-mixed`;
4. opzionale `broom-mixed`;
5. opzionale `caterpillar-mixed`.

Per `path`, `binary` e `star`, ogni arco viene orientato con probabilità `1/2`,
salvo campagne specifiche su orientazioni tutte concordi. Il generatore deve salvare
il seed e produrre lo stesso file su piattaforme diverse.

Il generatore mixed-star recuperato dal pacchetto RaC è un buon punto di partenza,
ma va riscritto nel nuovo formato e sottoposto ai test del nuovo repository.

### 8.3 Famiglie di coefficienti closure-specifiche

Proposta iniziale, da validare prima di generare gli archivi:

| Nome provvisorio | Generazione | Scopo |
|---|---|---|
| `independent-positive` | `p,w` indipendenti e positivi | Caso base, rapporti dispersi. |
| `independent-signed` | `p` con segno, `w>0` | Effetti di nodi localmente sfavorevoli. |
| `correlated` | `p = w + rumore` | Rapporti concentrati. |
| `anti-correlated` | relazione inversa con rumore | Rapporti più eterogenei. |
| `near-ties` | rapporti vicini ma distinti | Stress per confronti e breakpoint. |
| `exact-ties` | gruppi con rapporto identico | Canonicalizzazione e degenerazione. |

Queste classi possono ereditare le distribuzioni statistiche del test bed storico,
ma devono essere rinominate e motivate come casi numerici della parametric closure:
rapporti dispersi, coefficienti con segno, rapporti concentrati, near-ties ed
exact-ties. Non vanno presentate come classi knapsack e non richiedono citazioni al
KP nella nuova parte computazionale.

### 8.4 Identità e manifest delle istanze

Nome file proposto:

```text
pcf_<topology>_<coeff_class>_rho<rho>_n<n>_s<seed>.pcf
```

Ogni campagna deve produrre un manifest con:

- `instance_id` stabile;
- versione del generatore;
- seed;
- parametri;
- numero di nodi, archi e componenti;
- min/max dei coefficienti;
- SHA-256 del file;
- classificazione verificata della topologia.

---

## 9. Disegno sperimentale proposto

Il disegno va congelato **prima** di guardare i risultati completi.

### 9.1 Campagna A: correttezza small

- `n=1,...,10`;
- random forest, path, binary e star;
- tutte le famiglie di coefficienti;
- casi costruiti con exact ties e near ties;
- almeno 2.000 istanze complessive;
- oracle esaustivo + FMA/DFMA + HFMA/DHFMA + RaC;
- HIMA/HOMA quando applicabili.

Output: report di correttezza, nessun grafico prestazionale per il paper.

### 9.2 Campagna B: confronto random completo medium

Prima proposta:

- `n in {100,200,...,1000}`;
- topologia `mixed-forest`;
- `rho in {0.3,0.6,0.9,1.0}`;
- 6 famiglie di coefficienti;
- 10 seed;
- 2.400 istanze;
- FMA, HFMA e RaC su ogni istanza;
- verifica appaiata delle sequenze.

Questa matrice riprende una dimensione statisticamente leggibile, ma usa istanze
nuove e semantica closure-specifica.

### 9.3 Campagna C: random large

Proposta:

- `n in {10000,20000,...,100000}`;
- stessa matrice strutturale e di coefficienti della campagna medium;
- HFMA e RaC;
- FMA solo fino alla dimensione stabilita da un timeout preregistrato.

Il pacchetto RaC storico contiene solo campioni parziali per il large random. Per il
nuovo paper bisogna scegliere una delle due opzioni e dichiararla prima dei run:

1. matrice completa da 2.400 istanze; oppure
2. campione bilanciato preregistrato, uguale per ogni algoritmo.

Non si devono combinare risultati completi e parziali senza indicarlo.

### 9.4 Campagna D: strutture speciali RaC

- topologie: `path-mixed`, `binary-mixed`, `star-mixed`;
- dimensioni proposte:
  `100,200,500,1000,2000,5000,10000,20000,50000,100000`;
- 6 famiglie di coefficienti;
- 10 seed;
- HFMA e RaC appaiati;
- eventuale FMA soltanto sulle taglie compatibili con il timeout.

Questa campagna deve verificare esplicitamente la tesi sperimentale secondo cui
HFMA è competitivo sui casi random/path/binary mentre RaC è favorito sulle star.
I numeri presenti nel vecchio pacchetto non vanno copiati nel nuovo paper: devono
essere rigenerati con il codice e il protocollo definitivi.

### 9.5 Campagna E: algoritmi specializzati

Se HIMA/HOMA restano tra i contributi sperimentali del nuovo paper:

- in-forest: HFMA vs HIMA vs RaC;
- out-forest: HFMA vs HOMA vs RaC;
- medium e large con matrice bilanciata;
- confronto sia sui tempi sia sui contatori strutturali.

Se questa domanda scientifica viene rimossa dal paper, il codice resta testato ma la
campagna può essere esclusa.

### 9.6 Campagna F: baseline parametric pseudoflow

BPPF è pertinente come algoritmo generale di parametric closure. Si propone:

- versione upstream fissata tramite commit hash;
- build documentata e riproducibile;
- nuovo converter dal formato `.pcf` al formato BPPF;
- confronto sulla campagna medium mixed-forest;
- stessa definizione canonica dei breakpoint entro i limiti di precisione di BPPF;
- tempi e discrepanze riportati separatamente;
- nessun riferimento a capacità o PCKP nel converter.

Questa campagna è una decisione aperta: mantenerla rafforza il confronto con lo stato
dell'arte generale, ma richiede una gestione trasparente della precisione limitata.

---

## 10. Protocollo di misura

Il protocollo deve essere scritto in `docs/EXPERIMENTAL_PROTOCOL.md` prima dei run
ufficiali.

### 10.1 Ambiente

Registrare automaticamente:

- commit del nuovo repository;
- commit delle dipendenze esterne;
- compilatore e versione;
- flag CMake e flag di ottimizzazione;
- sistema operativo e kernel;
- modello CPU, numero di core e RAM;
- governor/frequenza CPU se accessibili;
- data UTC della campagna.

### 10.2 Esecuzione

- build `Release` pulita;
- processo single-thread;
- affinità a un core fisico, se possibile;
- ordine delle istanze randomizzato ma registrato;
- warm-up esplicito;
- almeno 3 ripetizioni per medium e 5 per i casi molto veloci, da confermare con
  un pilot;
- stessa istanza e stesso ordine per algoritmi confrontati;
- timeout deciso prima della campagna;
- nessun controllo di correttezza incluso nel timer;
- parsing, algoritmo e serializzazione misurati separatamente;
- wall time e CPU time entrambi registrati;
- memoria di picco registrata con un metodo uniforme.

### 10.3 Statistiche

Usare preferibilmente:

- mediana e intervallo interquartile per tempi appaiati;
- media solo quando serve confrontarsi con una convenzione già motivata;
- rapporti calcolati per istanza e poi aggregati, non soltanto rapporto tra medie;
- numero di timeout e failure sempre visibile;
- intervalli di confidenza bootstrap per i rapporti principali;
- log-log slope soltanto come descrizione empirica, non come prova di complessità.

---

## 11. Schema dei dati raw

Ogni riga deve rappresentare una singola ripetizione di un algoritmo su una istanza.

Colonne minime proposte:

```text
campaign_id
run_id
timestamp_utc
git_commit
instance_id
instance_sha256
topology
coefficient_class
rho
n_nodes
n_arcs
n_components
seed
algorithm
algorithm_version
repetition
status
correctness_status
sequence_sha256
n_breakpoints
n_layers
parse_cpu_ms
algorithm_cpu_ms
algorithm_wall_ms
verify_cpu_ms
peak_rss_kib
timeout_s
```

Per RaC aggiungere contatori come:

```text
rac_clusters
rac_joins
rac_rakes
rac_compress1
rac_compress2
rac_rounds
rac_max_depth
rac_envelope_pieces
rac_exact_comparisons
```

Per HFMA aggiungere contatori corrispondenti alle operazioni dominanti, in modo che
il confronto non si limiti ai tempi macchina.

I dati raw non devono essere corretti manualmente. Eventuali esclusioni devono essere
espresse da uno script e da una colonna con la motivazione.

---

## 12. Piano di riscrittura della parte computazionale del paper

La riscrittura del manoscritto è una fase distinta dall'implementazione e dai
benchmark. Non deve iniziare finché il nuovo codice, le nuove istanze e i risultati
principali non hanno superato i gate di correttezza. Questa sezione definisce però
fin da ora come dovrà essere ricostruita la parte computazionale.

Il target editoriale è esclusivamente la **versione v2 del nuovo manoscritto**. La
versione arXiv/v1, il relativo sorgente e i PDF storici non saranno aggiornati
retroattivamente. Prima di qualsiasi modifica verrà identificato e confermato il
nome definitivo del file sorgente v2.

### 12.1 Obiettivo editoriale

La nuova sezione deve essere leggibile come parte di un paper interamente dedicato
alla **parametric closure su foreste orientate**. Un lettore non deve avere bisogno
di conoscere il knapsack con precedenze per comprendere:

- il problema risolto;
- il significato delle istanze;
- gli algoritmi confrontati;
- la definizione dei breakpoint e delle sequenze restituite;
- le metriche di correttezza e prestazione;
- il ruolo di FMA, HFMA, HIMA, HOMA, RaC e BPPF.

Nella parte computazionale definitiva non devono comparire:

- PCKP o precedence-constrained knapsack;
- capacità della knapsack;
- soluzione primale della rilassata LP;
- split item o split macroitem;
- percentuale della capacità;
- objective value della knapsack;
- classi di istanze motivate attraverso la letteratura KP;
- riferimenti al fatto che il codice nasce da un precedente esperimento KP.

Il rapporto con il precedente paper arXiv è un fatto di provenienza del software,
da documentare nel repository nuovo, non il quadro concettuale degli esperimenti del
nuovo paper.

### 12.2 Terminologia da usare

Tabella di conversione proposta:

| Terminologia da eliminare dalla parte computazionale | Terminologia nuova proposta |
|---|---|
| item | node/vertex, salvo che il paper mantenga formalmente “item” |
| profit `p_i` | profit `p_i` |
| weight `w_i` | positive weight `w_i` |
| profit-to-weight ratio | breakpoint ratio `P(M)/W(M)` |
| feasible knapsack solution | closed set/closure |
| optimal LP solution | optimal closure at `lambda` |
| knapsack capacity | eliminare senza sostituzione |
| split macroitem | eliminare senza sostituzione |
| used capacity | eliminare senza sostituzione |
| objective value PCKP | parametric closure value, solo quando serve |
| precedence graph | directed closure graph |
| precedence constraint | closure implication/closure arc |
| KP coefficient class | affine-coefficient family |

La notazione del paper (`p/w`, `P/W`, `lambda`, macroitems) deve essere identica in
modello, codice, formato delle istanze, didascalie, tabelle e testo. Non si devono
mantenere nomi diversi soltanto per comodità del codice portato.

### 12.3 Struttura proposta della nuova sezione computazionale

La struttura seguente sostituisce l'attuale sezione costruita per estensione del
vecchio paper.

#### 12.3.1 Experimental goals and research questions

Aprire la sezione con domande sperimentali esplicite:

1. HFMA è effettivamente preferibile alla versione FMA con scansione diretta?
2. Qual è la scalabilità empirica di HFMA sulle foreste con orientazione arbitraria?
3. Quanto guadagnano HIMA e HOMA quando l'orientazione è specializzata?
4. Come si confrontano HFMA e RaC sulle foreste casuali?
5. Quali strutture favoriscono RaC e quali favoriscono HFMA?
6. Come si confrontano gli algoritmi forest-specifici con un metodo generale di
   parametric flow come BPPF?

Ogni sottosezione successiva deve rispondere a una di queste domande. Se una domanda
non è sostenuta da una campagna completa, va eliminata o presentata esplicitamente
come esperimento esplorativo.

#### 12.3.2 Algorithms and implementations

Presentare in modo compatto:

- FMA come implementazione di riferimento a scansione;
- HFMA come variante pratica heap-based;
- HIMA/HOMA come varianti per orientazioni speciali, se mantenute;
- RaC come implementazione rake-and-compress/top-tree;
- BPPF come baseline generale bounded-precision, se mantenuta;
- oracle esaustivo e max-flow soltanto come strumenti di validazione, non come
  concorrenti temporali principali.

Per ogni algoritmo indicare dominio, output, aritmetica, complessità teorica rilevante
e criteri di canonicalizzazione. Non descrivere componenti software che sono state
eliminate dal nuovo repository, come solver LP o ricostruzione della soluzione
knapsack.

#### 12.3.3 Validation methodology

Questa sottosezione deve precedere i risultati temporali e dichiarare:

- confronto con enumerazione completa sulle istanze small;
- verifica max-flow negli intervalli tra breakpoint;
- confronti differenziali tra algoritmi;
- numero esatto di istanze validate;
- trattamento di ties e degenerazioni;
- assenza o elenco completo degli eventuali mismatch.

In questo modo l'affidabilità di RaC non dipende soltanto dal confronto con HFMA.

#### 12.3.4 Instance generation

Descrivere le istanze direttamente come coppia tra:

1. una foresta orientata;
2. coefficienti affini interi `p_i - lambda w_i`.

La sottosezione deve includere:

- topologie random e strutturate;
- distribuzioni closure-specifiche dei coefficienti;
- intervalli e segni ammessi;
- densità `rho`;
- dimensioni;
- seed;
- numero di repliche;
- regola di orientamento;
- formato e disponibilità dei manifest.

Non si devono chiamare le famiglie “knapsack classes” né citarne la provenienza KP.
Se si decide di mantenere distribuzioni statisticamente simili alle vecchie, esse
vanno ridefinite autonomamente come famiglie di coefficienti affini e motivate per
la loro capacità di produrre rapporti dispersi, concentrati, quasi uguali o uguali.

#### 12.3.5 Experimental environment and protocol

Riportare hardware, compilatore, flag, single-threading, affinità CPU, ripetizioni,
warm-up, timeout, memoria e statistica aggregata. Specificare che:

- il timer misura soltanto l'algoritmo;
- parsing, verifica e scrittura non sono inclusi;
- i confronti sono appaiati sulla stessa istanza;
- la sequenza prodotta viene verificata fuori dal timer;
- tutti i dati raw sono disponibili.

#### 12.3.6 FMA versus HFMA

Riscrivere la giustificazione dell'heap nel solo linguaggio della parametric closure.
Riportare tempi e contatori operativi sulle nuove istanze. Nessun valore proveniente
dai vecchi CSV può essere mantenuto automaticamente.

La conclusione ammessa deve derivare dai nuovi dati, ad esempio: quando il costo
delle scansioni ripetute supera il costo di mantenimento dell'heap e come cambia il
rapporto al crescere di `n`.

Inserire esplicitamente anche il controcaso delle **stelle a orientazione mista**.
Nel pilot indipendente del 2026-08-28, FMA è risultata da circa 2.8 volte a 4.9
volte più veloce di HFMA tra `n=100` e `n=2,000`
(`results/FMA_VS_HFMA_STAR_2026-08-28.md`). La spiegazione da riportare è
operativa, non soltanto empirica: un aggiornamento del nodo centrale modifica o
invalida un gran numero di rapporti candidati; l'heap lazy accumula quindi molte
voci stale e richiede numerosi aggiornamenti/scarti. La scansione diretta di FMA
non paga tale manutenzione. Il risultato finale dovrà essere confermato dalla
campagna con ordine di esecuzione randomizzato e contatori di invalidazioni,
inserimenti e pop stale della heap.

#### 12.3.7 HFMA scaling on arbitrarily oriented forests

Mostrare la scalabilità sulle nuove `mixed-forest`/`mixed-tree`. Separare chiaramente:

- complessità worst-case dimostrata;
- crescita empirica osservata;
- effetto di densità, coefficient class e numero di layers;
- contatori di aggiornamento della heap.

Una regressione log-log può essere descrittiva, ma non deve essere presentata come
dimostrazione della complessità.

#### 12.3.8 Specialized orientations

Se mantenuta, questa sottosezione confronta:

- HIMA con HFMA e RaC sulle in-forest;
- HOMA con HFMA e RaC sulle out-forest.

I rapporti devono essere calcolati per istanza e poi aggregati. L'eventuale esclusione
di questa sottosezione non comporta necessariamente la rimozione degli algoritmi dal
repository: possono restare come implementazioni testate.

#### 12.3.9 General parametric-flow baseline

Il confronto BPPF deve essere presentato come confronto fra:

- algoritmi che sfruttano la struttura di foresta;
- un algoritmo di parametric flow applicabile a grafi più generali.

Descrivere conversione dei coefficienti, precisione, scaling interno e possibili
overflow. Le discrepanze causate dalla precisione limitata devono essere elencate e
non trasformate automaticamente in equivalenze mediante tolleranze post hoc.

Non menzionare la capacità o la formulazione PCKP usata dal vecchio adapter.

#### 12.3.10 HFMA versus RaC on random forests

Questa è una sottosezione nuova e centrale. Deve includere:

- matrice completa o campione preregistrato;
- tempi appaiati;
- memoria;
- numero di breakpoint/layers;
- contatori strutturali di entrambi gli algoritmi;
- distribuzione, non soltanto media, del rapporto `RaC/HFMA`;
- analisi per densità e famiglia di coefficienti;
- timeout e failure.

I risultati parziali già presenti nel pacchetto RaC servono a progettare la campagna,
ma non possono essere copiati nel testo definitivo.

#### 12.3.11 Structured-tree stress tests

Separare path, binary e mixed star dai test random. Questa sottosezione deve spiegare
perché ciascuna forma è rilevante per le operazioni dei due algoritmi:

- path: profondità e compress;
- binary: struttura gerarchica bilanciata;
- mixed star: caso sfavorevole per HFMA; gli aggiornamenti del centro invalidano
  molti rapporti nel heap lazy, mentre FMA evita questo costo di manutenzione e
  RaC è favorito dalle rake.

Riportare tempi, memoria e contatori RaC. Quando HFMA raggiunge il timeout, mostrare
il timeout come dato censurato e non stimarne artificialmente il tempo.

#### 12.3.12 Computational conclusions

Chiudere con conclusioni limitate a ciò che i dati dimostrano:

- correttezza osservata;
- regione in cui HFMA è preferibile;
- regione in cui RaC è preferibile;
- costo in memoria di RaC;
- vantaggio delle varianti specializzate;
- differenza di dominio rispetto al baseline generale BPPF.

Evitare formulazioni assolute come “state of the art” se non sono sostenute da un
confronto completo e aggiornato.

### 12.4 Riscrittura delle figure e delle tabelle

Tutte le coordinate numeriche attualmente scritte direttamente nel sorgente LaTeX
devono essere sostituite da output della pipeline.

Set minimo proposto:

1. FMA vs HFMA su random medium/selected large;
2. scaling HFMA su mixed forests large;
3. HIMA/HOMA vs algoritmi generali, se mantenuti;
4. HFMA vs BPPF, se mantenuto;
5. HFMA vs RaC su random forests;
6. distribuzione del rapporto RaC/HFMA per densità;
7. HFMA vs RaC su path e binary;
8. HFMA vs RaC su mixed star;
9. memoria e numero di envelope pieces di RaC;
10. tabella riassuntiva di correttezza, mismatch e timeout.

Ogni figura deve dichiarare:

- unità di misura;
- aggregazione usata;
- numero di istanze;
- numero di ripetizioni;
- presenza di timeout;
- file raw/processed da cui è stata generata.

### 12.5 Riscrittura di Instance Generation e Code/Data Availability

L'attuale descrizione delle istanze va sostituita interamente con quella del nuovo
generatore closure-specifico. L'eventuale appendice `Instance Generation` deve essere
coerente con la sezione computazionale e con `docs/INSTANCE_FORMAT.md`.

La dichiarazione `Code and Data Availability` deve puntare soltanto a:

- nuovo repository del paper sulla parametric closure;
- release esatta usata per gli esperimenti;
- nuovo archivio delle istanze;
- nuovi raw data;
- commit/versione di BPPF, se usato.

Non deve presentare il vecchio GitHub arXiv come repository del nuovo paper. Il
repository storico può essere citato separatamente soltanto se serve documentare la
provenienza di una parte del software, senza confondere le due release.

### 12.6 Regole sulle citazioni nella parte computazionale

Le citazioni ammesse devono riguardare:

- maximum closure e parametric closure;
- parametric max-flow/min-cut;
- pseudoflow/BPPF;
- tree contraction, rake-and-compress e top trees;
- metodologia sperimentale, se necessaria.

Le citazioni usate esclusivamente per presentare PCKP, knapsack classico, classi di
istanze KP o capacità devono essere eliminate dalla parte computazionale. La
bibliografia complessiva del paper può naturalmente contenere altri riferimenti se
necessari alle sezioni teoriche: il vincolo qui riguarda la narrazione e la
motivazione degli esperimenti.

### 12.7 Procedura editoriale

La riscrittura riguarda soltanto la versione v2 e deve avvenire in questo ordine:

1. congelare codice, generatori e protocollo;
2. completare la campagna ufficiale;
3. validare raw data e risultati aggregati;
4. generare figure e tabelle;
5. preparare la nuova sezione computazionale della v2 in un file `.tex` separato;
6. revisionare insieme quel file senza modificare ancora il manoscritto principale;
7. integrare la sezione soltanto dopo approvazione;
8. aggiornare abstract, introduzione, conclusioni e Code/Data Availability per
   renderli coerenti con i risultati effettivi;
9. compilare e controllare tutte le cross-reference;
10. svolgere un audit terminologico finale.

### 12.8 Gate editoriale “zero KP”

Prima dell'integrazione, una ricerca automatica sulla nuova sezione computazionale
deve trovare zero occorrenze non giustificate dei termini:

```text
knapsack
PCKP
capacity
split item
split macroitem
profit
weight
```

`profit` e `weight` sono inclusi perché devono essere sostituiti dalla notazione
affine definitiva. Eventuali occorrenze in citazioni bibliografiche, nomi storici o
frasi di provenienza devono essere esaminate manualmente e mantenute soltanto se
indispensabili.

Checklist di accettazione:

- [ ] Il problema computazionale è definito autonomamente come parametric closure.
- [ ] Nessun input o output contiene una capacità.
- [ ] Tutte le istanze della nuova release sono migrate o rigenerate in modo
      riproducibile e documentate tramite manifest/checksum e provenienza legacy.
- [ ] Le famiglie di coefficienti hanno motivazione closure-specifica.
- [ ] RaC è descritto e misurato con l'implementazione sottoposta ad audit.
- [ ] Tutte le affermazioni numeriche derivano dalla nuova pipeline.
- [ ] Figure e tabelle non contengono coordinate hardcoded non tracciate.
- [ ] Code/Data Availability punta alla nuova release indipendente.
- [ ] Abstract, introduzione e conclusioni non contraddicono i risultati.
- [ ] Il materiale arXiv/GitHub storico non è stato modificato.

---

## 13. Pipeline di analisi e collegamento futuro al paper

Il flusso deve essere unidirezionale:

```text
istanze + manifest
        -> run raw immutabili
        -> validazione schema/checksum
        -> dati processati
        -> tabelle e figure
        -> frammenti LaTeX generati
```

Gli script devono produrre:

- CSV aggregati;
- tabelle `.tex`;
- figure PDF/PNG;
- un file `results_summary.json` con tutti i numeri citabili;
- un report delle discrepanze e dei timeout.

Il manoscritto non va modificato durante questa fase di progettazione. Dopo la
validazione dei risultati, si deciderà insieme quali tabelle/figure importare e quali
affermazioni aggiornare.

---

## 14. Riproducibilità e pubblicazione

### 14.1 Repository nuovo

Il repository nuovo deve essere **completamente indipendente e autosufficiente**.
Deve contenere sotto un'unica identità pubblica:

- il codice closure-specifico effettivamente usato negli esperimenti;
- FMA/DFMA, HFMA/DHFMA e le eventuali varianti HIMA/HOMA portate e verificate;
- il nuovo algoritmo RaC/top-tree sottoposto ad audit;
- la CLI e le librerie necessarie a eseguire tutti gli algoritmi;
- oracle esaustivo e max-flow;
- test CTest, fixture e configurazione CI;
- generatori e convertitori delle istanze;
- manifest di provenienza dal dataset storico;
- piccole istanze versionate direttamente;
- accesso automatico e verificato agli archivi completi delle nuove istanze;
- script di benchmark e protocollo sperimentale;
- pipeline di validazione, aggregazione, tabelle e figure;
- raw data e risultati processati, direttamente o come asset di release;
- documentazione completa per build e riproduzione da clone pulito.

Il commit/tag pubblicato deve essere lo stesso codice compilato per la campagna
ufficiale. Non è ammesso pubblicare una ricostruzione successiva o una copia diversa
da quella realmente eseguita.

Il repository non deve contenere dipendenze per path verso il workspace locale, né
remote o script che puntino in scrittura ai vecchi GitHub. Può riportare link
read-only al paper arXiv e ai repository storici soltanto in `PROVENANCE.md`.

### 14.1.1 Test di indipendenza del nuovo GitHub

Prima della pubblicazione si deve eseguire una prova da ambiente pulito:

1. clone del nuovo repository in una directory vuota;
2. download degli asset tramite gli script documentati;
3. verifica automatica dei checksum;
4. configurazione e compilazione senza accesso alle cartelle legacy;
5. esecuzione completa di CTest;
6. generazione di un piccolo set di istanze;
7. conversione di una fixture ereditata;
8. esecuzione di FMA, HFMA e RaC;
9. confronto con gli oracle;
10. smoke run della pipeline fino a tabella e figura.

Il gate è superato soltanto se tutte queste operazioni funzionano senza
`CODE_FOREST`, `GITHUB`, `PAPER` o altri file del vecchio workspace.

### 14.2 Release

Una release del paper dovrebbe contenere:

- source tarball del commit usato;
- manifest completo;
- archivi delle istanze;
- CSV raw compressi;
- CSV processati;
- figure e tabelle;
- log dell'ambiente;
- checksum SHA-256;
- istruzioni `reproduce.sh` o comandi equivalenti non distruttivi.

### 14.3 Container opzionale

Valutare un container per fissare compilatore e dipendenze. Il container non risolve
la riproducibilità dei tempi hardware, ma rende riproducibili build, correttezza e
analisi.

---

## 15. Fasi operative e gate

### Fase 0 — Congelamento del legacy

Deliverable:

- inventario e checksum del materiale legacy;
- dichiarazione che il nuovo progetto non vi dipende;
- nessuna modifica ai vecchi GitHub.

Gate: approvazione della separazione tra paper arXiv e nuovo paper.

### Fase 1 — Scheletro indipendente

Deliverable:

- nuova directory/repository;
- nuovo modello `Instance` closure-specifico;
- razionali esatti;
- parser `.pcf`;
- CMake/CTest/CI funzionanti.

Gate: il progetto compila e testa senza accesso alle directory legacy.

### Fase 2 — Porting FMA/DFMA/HFMA/DHFMA/HIMA/HOMA

Deliverable:

- porting con provenienza;
- rimozione completa di capacità e semantica KP;
- equivalenza sui test controllati;
- contatori operativi.

Gate: oracle small e test differenziali tutti superati.

### Fase 3 — Recupero RaC

Deliverable:

- estrazione controllata del C++ top-tree;
- `RAC_AUDIT.md`;
- porting al nuovo modello;
- test unitari di envelope/rake/compress;
- test top-down e canonicalizzazione.

Gate: RaC supera oracle, differential test e sanitizer.

### Fase 4 — Generatori e istanze

Deliverable:

- convertitore deterministico dal formato legacy al formato `.pcf`;
- generatori closure-specifici compatibili con le famiglie ereditate;
- random/path/binary/star;
- manifest di provenienza e checksum source/target;
- archivio small e pilot medium.

Gate: riproducibilità byte-per-byte su due esecuzioni indipendenti.

### Fase 5 — Pilot sperimentale

Deliverable:

- stima dei tempi per matrice completa;
- scelta ripetizioni e timeout;
- controllo memoria RaC;
- schema CSV definitivo;
- congelamento della matrice.

Gate: approvazione congiunta del protocollo definitivo.

### Fase 6 — Campagna ufficiale

Deliverable:

- raw data immutabili;
- log ambiente;
- report automatico di correttezza;
- nessun mismatch non spiegato.

Gate: tutti i file passano validazione schema, completezza e checksum.

### Fase 7 — Analisi e figure

Deliverable:

- aggregati riproducibili;
- tabelle e figure;
- report su timeout/discrepanze;
- elenco puntuale delle affermazioni supportate.

Gate: revisione scientifica congiunta prima di toccare il manoscritto.

### Fase 8 — Pubblicazione separata

Deliverable:

- nuovo GitHub autosufficiente contenente il codice realmente usato, incluso RaC;
- nuove istanze direttamente accessibili dal nuovo GitHub o dalle sue release;
- release versionata;
- eventuale deposito dati/DOI;
- istruzioni di riproduzione verificate su clone pulito.

Gate: nessuna modifica o sovrascrittura dei repository del paper arXiv.

---

## 16. Rischi principali

| Rischio | Mitigazione proposta |
|---|---|
| Il C++ RaC recuperato non coincide esattamente con il nuovo pseudocodice | Audit matematico obbligatorio e mapping operazione-per-operazione. |
| Overflow nei confronti razionali/envelope | `__int128`, controlli espliciti e limiti documentati. |
| Due algoritmi coincidono perché condividono lo stesso errore | Oracle esaustivo e max-flow indipendenti. |
| I risultati RaC archiviati sono parziali | Rerun completo con matrice congelata. |
| HFMA va in timeout sulle star grandi | Timeout preregistrato e analisi trasparente dei dati censurati. |
| RaC usa molta memoria | Misura RSS e contatori di envelope; pilot prima del large. |
| Terminologia KP ricompare nel codice o nei dati | Review automatica dei nomi e review manuale della documentazione. |
| Il nuovo progetto altera accidentalmente il legacy | Directory e repository separati; nessun remote/script legacy. |
| Il nuovo progetto dipende implicitamente da file locali legacy | Test obbligatorio da clone pulito senza accesso al vecchio workspace. |
| La migrazione delle istanze perde la corrispondenza storica | Convertitore deterministico, checksum source/target e manifest di provenienza. |
| Risultati hardcoded nel paper | Tabelle e figure generate dalla pipeline. |

---

## 17. Decisioni da validare insieme

Prima di implementare sono necessarie decisioni esplicite su:

1. nome della nuova directory e del futuro repository;
2. notazione del paper `p/w`, da mantenere identica in tutto il progetto;
3. nome pubblico degli algoritmi: FMA/HFMA/RaC oppure nomi più closure-specifici;
4. inclusione o esclusione della campagna HIMA/HOMA;
5. inclusione o esclusione del confronto BPPF;
6. sei famiglie definitive di coefficienti;
7. matrice large completa oppure campione bilanciato preregistrato;
8. lista definitiva delle strutture speciali oltre a path/binary/star;
9. numero di ripetizioni e timeout, dopo il pilot;
10. macchina sulla quale eseguire i run ufficiali;
11. destinazione degli archivi grandi e dei raw data;
12. regola canonica definitiva per breakpoint uguali;
13. conversione esatta di tutte le istanze storiche oppure rigenerazione selettiva;
14. nome/percorso definitivo del sorgente v2 che sarà modificato soltanto dopo la
    validazione computazionale.

---

## 18. Primo blocco di lavoro dopo l'approvazione

Una volta validato questo piano, il primo blocco operativo dovrebbe limitarsi a:

1. creare lo scheletro del nuovo repository;
2. definire `Instance`, `Rational` e `ParametricSequence`;
3. implementare parser e validazione del formato `.pcf`;
4. implementare l'oracle esaustivo small;
5. portare FMA come prima implementazione di riferimento;
6. costruire test CTest reali;
7. presentare i risultati dei test prima di portare HFMA e RaC.

In questo modo la base semantica e la verifica indipendente vengono fissate prima
di introdurre le implementazioni più complesse e prima di generare nuovi risultati.
