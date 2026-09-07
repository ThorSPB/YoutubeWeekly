# Istoric versiuni

## Unreleased
- **Videoclipurile pentru copii se descarcă din nou, la calitate maximă**: Videoclipurile marcate „Made for Kids” pe YouTube — cântece pentru copii, istorioare biblice și altele — eșuau toate cu „Acest videoclip nu este disponibil”, deși se redau perfect în browser. YouTube le reține dacă aplicația nu poate rula o bucată din codul lui, așa că aplicația include acum micul motor necesar. Se descarcă din nou la 1080p complet, iar un link care tot refuză este reîncercat pe a doua cale înainte ca aplicația să renunțe
- **Pictogramă mai clară**: Pictograma era livrată într-o singură dimensiune mică, așa că Windows o întindea pentru scurtături, foldere și notificări — arăta neclară aproape peste tot. Acum include toate dimensiunile cerute de Windows, până la 256px

## v1.6.0
- **Bara nu mai rămâne blocată la 50%**: Descărcările care vin ca un singur fișier — un mp3 sau un video servit direct de dezvoltator — lăsau bara blocată la jumătate pentru totdeauna, chiar dacă descărcarea se terminase. Rezolvat
- **Bară de progres corectă**: Bara urmărește acum câți octeți au rămas de fapt, în loc să dea câte o jumătate imaginii și sunetului. La o descărcare 1080p sunetul este o parte mică din total, așa că bara nu mai avansează greu și apoi sare brusc
- **Descărcările eșuate nu mai par blocate**: Când o descărcare eșuează, bara de progres este acum ascunsă, în loc să rămână pe ecran umplută pe jumătate
- **Butonul Descarcă îți păstrează și el videoclipul**: Aceeași corecție ca la descărcarea automată — apăsarea butonului Descarcă nu mai șterge videoclipul de săptămâna trecută înainte de a-l aduce pe cel nou, așa că o eroare nu te mai poate lăsa fără nimic
- **Notele de lansare acoperă tot ce ai ratat**: Actualizarea peste mai multe versiuni afișa doar notele celei mai recente lansări — un salt de la 1.4.0 la 1.5.1 ascundea tot ce s-a schimbat în 1.5.0. Acum vezi fiecare lansare de la versiunea pe care o aveai
- **Note de lansare în română**: Notele de lansare sunt acum traduse și urmează setarea de limbă a aplicației
- **Buton pentru notele de lansare**: Setări → Avansat → Note de lansare deschide istoricul complet într-un cititor cu derulare
- **Se deschide în față după actualizare**: Actualizarea în timp ce aplicația era pe ecran o readucea minimizată în bara de sistem. Acum revine așa cum ai lăsat-o — iar o actualizare care se instalează singură în timp ce aplicația stă în bara de sistem rămâne acolo și îți arată notele la următoarea deschidere
- **Coloană pentru tipul fișierului**: Vizualizările de foldere au acum o coloană proprie Tip, ca să poți distinge întotdeauna un MP4 de un MP3 fără să lărgești fereastra
- **Pictograma aplicației pe fiecare fereastră**: Ferestrele de setări, de foldere și de ajutor afișau o pictogramă generică în loc de cea a aplicației. Rezolvat
- **Descărcările respectă setarea ta de calitate**: Când dezvoltatorul oferă un videoclip direct (folosit când titlurile de pe YouTube împiedică găsirea lui), acesta vine acum în calitatea aleasă de tine, în loc de cea mai mare de fiecare dată

## v1.5.1
- **Descărcările funcționează din nou**: YouTube a schimbat ceva în august, iar componenta de descărcare a aplicației nu mai făcea față, așa că toate descărcările eșuau. A fost actualizată — descărcările funcționează din nou
- **Videoclipul tău rămâne până sosește cel nou**: Aplicația ștergea videoclipul de săptămâna trecută *înainte* de a-l aduce pe cel nou, așa că o descărcare eșuată te lăsa fără nimic. Acum videoclipul vechi este șters doar după ce cel nou a fost descărcat cu succes
- **Fără videoclipuri fără sunet**: O descărcare oprită la jumătate lăsa în urmă un fișier cu imagine, dar fără sunet, iar aplicația îl oferea ca și cum ar fi fost complet. Descărcările neterminate sunt acum șterse și nu mai sunt afișate sau redate
- **Reîncercările chiar reîncearcă**: Un fișier neterminat rămas în urmă făcea aplicația să creadă că videoclipul era deja descărcat, așa că refuza să încerce din nou. Rezolvat

## v1.5.0
- **Corecții pentru videoclipuri**: Când un canal urcă un videoclip cu data greșită în titlu, aplicația nu îl mai găsește. Dezvoltatorul poate acum îndrepta aplicația direct spre videoclipul corect, iar acesta se descarcă normal — fără actualizare sau reinstalare
- **Videoclipuri găzduite direct**: O corecție poate oferi și un fișier video găzduit direct, nu doar un link YouTube
- **Corecții în timpul rulării**: Aplicația observă acum o corecție publicată după pornirea ei, în loc să verifice o singură dată la lansare. O corecție forțată înlocuiește un videoclip deja descărcat pentru Sabatul respectiv
- **Consum mic de rețea**: Verificările sunt ieftine (câteva sute de octeți când nu s-a schimbat nimic), dese doar vineri și sâmbătă și rare în restul săptămânii

## v1.4.0
- **Limba română**: Traducere completă în română — schimbă din Setări → General → Limbă
- **Comutare limbă**: Alege între English și Română, se aplică imediat
- **Corecție pornire cu sistemul**: După actualizarea de la versiuni mai vechi, aplicația uneori nu pornea efectiv la deschiderea calculatorului, deși setarea era activă — rezolvat, acum se reînregistrează la fiecare pornire
- **Sortare după dată**: Listele de videoclipuri descărcate sunt acum sortate cu cele mai noi primele, în loc de alfabetic — mult mai bine pentru folderul Altele
- **Migrarea setărilor**: Setările noi apărute odată cu actualizările apar acum automat, fără să fie nevoie să deschizi fereastra de setări

## v1.3.1
- **Răspuns către dezvoltator**: Poți acum răspunde mesajelor dezvoltatorului direct în fereastra de feedback
- **Mai multe capturi de ecran**: Atașează mai multe imagini la feedbackul tău
- **Indicator de notificare**: O bulină roșie pe butonul 💬 arată când dezvoltatorul a răspuns
- **Vizualizare îmbunătățită a conversațiilor**: Vezi cel mai recent mesaj din fiecare conversație și evidențieri verzi pentru răspunsurile noi
- **Corecție derulare**: Rotița mouse-ului funcționează acum corect oriunde în fereastra de feedback
- **Corecție revenire la versiune**: Butonul de revenire la o versiune anterioară este acum vizibil corect

## v1.3.0
- **Feedback în aplicație**: Trimite raportări de erori, propuneri de funcționalități sau feedback general direct din aplicație
- **Capturi de ecran**: Atașează capturi de ecran la feedback pentru a ușura identificarea problemei
- **Conversație**: Vezi răspunsurile dezvoltatorului și urmărește starea feedbackului tău
- **Informații despre sistem**: Detaliile despre componente sunt incluse în feedback pentru a ajuta la diagnosticarea problemelor

## v1.2.0
- **Statistici de utilizare**: Datele anonime de utilizare ajută la îmbunătățirea aplicației — arată câți oameni o folosesc și ce funcții sunt populare
- **Renunțare**: Dezactivează ușor statisticile din Setări → General → „Trimite date anonime de utilizare”
- **Urmărire pentru Altele**: Descărcările din secțiunea „Altele” sunt acum urmărite separat, împreună cu calitatea aleasă
- **Confidențialitate în primul rând**: Localizarea este determinată pe dispozitivul tău — adresa ta IP nu ne este niciodată trimisă

## v1.1.3
- **Revenire la o versiune anterioară**: Revino la orice versiune anterioară din Setări → Avansat → Revenire
- **Instalare automată a actualizărilor**: Instalează automat actualizările la pornire (fără fereastră de confirmare, doar se actualizează)
- **Dezactivarea verificării actualizărilor**: Opțiune de a opri verificarea automată a actualizărilor
- **Setări cu file**: Setările au fost reorganizate în filele General, Player și Avansat

## v1.1.2
- **Actualizări automate la pornire**: Instalează automat actualizările când aplicația rulează în bara de sistem
- **Buton de verificare a actualizărilor**: Verifică actualizările oricând cu butonul ↻
- **Note de lansare după actualizare**: Vezi ce este nou după fiecare actualizare
- **Starea actualizării**: Mesajul „Actualizare completă!” este afișat la prima pornire după o actualizare

## v1.1.1
- **Afișarea versiunii**: Versiunea curentă este afișată în colțul din stânga jos al aplicației
- **Corecție cale videoclipuri**: Calea folderului de videoclipuri se resetează acum corect când aplicația este mutată în altă locație
- **Corecții actualizare automată**: Fiabilitate îmbunătățită a procesului de actualizare pe Windows

## v1.1.0
- **Actualizări automate**: Aplicația se actualizează acum singură — apasă „Actualizează acum” când ești întrebat
- **Opțiuni de calitate superioară**: Au fost adăugate opțiunile max, 4K și 2K, alături de cele existente 1080p/720p/480p/mp3
- **Potrivire mai inteligentă a videoclipurilor**: Tolerează greșelile obișnuite din titluri (dată greșită cu o zi, probleme de formatare) și cere confirmarea
- **Afișarea versiunii**: Versiunea curentă este acum afișată în colțul din stânga jos

## v1.0.4
- Prima versiune publică
- Descărcări automate vineri și sâmbătă
- Suport pentru mai multe canale (Departamentul Isprăvnicie, ScoalaDeSabat)
- Integrare în bara de sistem, cu pornire odată cu sistemul
- Integrare cu playerul MPV și setări personalizate
