# Setări - Ghid de configurare

## 📁 Setări fișiere și foldere

### Folder videoclipuri
- **Implicit**: `data/videos/`
- **Scop**: Locul unde sunt stocate toate videoclipurile descărcate

### Păstrează videoclipurile vechi
- **Activat**: Previne ștergerea automată a videoclipurilor din săptămâna anterioară
- **Dezactivat**: Păstrează doar cel mai recent videoclip per canal (economisește spațiu) - Recomandat

## ⚡ Setări de descărcare

### Calitate implicită
- **1080p**: Cea mai bună calitate, fișiere mari
- **720p**: Calitate bună, dimensiune moderată
- **480p**: Calitate mai mică, fișiere mici
- **mp3**: Doar audio

### Activează descărcarea automată - Recomandat
- **Când**: Rulează vineri și sâmbătă
- **Ce**: Descarcă automat videoclipurile pentru sâmbăta următoare
- **Cerință**: Trebuie activat pentru funcționare automată

## 🔔 Setări de sistem

### Activează notificările - Recomandat
- Afișează notificări de sistem când descărcările se finalizează sau eșuează

### Pornește cu sistemul (minimizat în tray) - Recomandat
- **Activat**: Aplicația pornește când computerul pornește (minimizată în tray)
- **Folosește**: Registrul Windows pentru gestionarea pornirii
- **Perfect pentru**: Funcționare automată în fundal

## 🎵 Setări player media

### Folosește MPV Player - Recomandat
- **Implicit**: Folosește playerul video implicit al sistemului
- **MPV**: Folosește playerul MPV inclus cu opțiuni personalizate
- **Beneficii**: Suport mai bun pentru codecuri, setări personalizate

### Configurare MPV
- **Ecran complet**: Pornește videoclipurile pe tot ecranul
- **Volum**: Setează volumul implicit de redare (0-130)
- **Monitor**: Alege pe care monitor să fie ecranul complet (setări multi-monitor)
- **Argumente personalizate**: Argumente avansate pentru linia de comandă MPV

## 💾 Opțiuni avansate

### Resetare la valorile implicite
- Restaurează toate setările la valorile originale
- **Atenție**: Nu poate fi anulat
- Folosește dacă setările devin corupte sau dorești un start nou

### Căi executabile
- **Căile MPV/FFmpeg**: Gestionate automat
- **Căi personalizate**: Utilizatorii avansați pot specifica instalări personalizate - Nu este recomandat

## 🔧 Depanare

### Descărcările eșuează
1. Verifică conexiunea la internet
2. Verifică manual canalele pentru a vedea dacă videoclipurile au fost încărcate

### Probleme cu playerul
1. Încearcă să dezactivezi „Folosește MPV Player" pentru a folosi playerul implicit
2. Verifică dacă fișierele video nu sunt corupte
3. Verifică setările MPV în opțiunile avansate

### Probleme la pornire
1. Verifică permisiunile registrului Windows
2. Dezactivează/reactivează „Pornește cu sistemul"
3. Rulează ca administrator dacă este necesar