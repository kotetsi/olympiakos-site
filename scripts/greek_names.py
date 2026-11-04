"""Ελληνικά ονόματα ομάδων Super League (κοινά για αρχείο και φετινή σεζόν)."""
NAME = {
    "Panathinaikos": "Παναθηναϊκός", "AEK": "ΑΕΚ", "AEK Athen": "ΑΕΚ", "AEK Athens": "ΑΕΚ",
    "PAOK": "ΠΑΟΚ", "PAOK Saloniki": "ΠΑΟΚ", "Aris": "Άρης", "Aris Saloniki": "Άρης",
    "OFI": "ΟΦΗ", "OFI Heraklion": "ΟΦΗ", "Asteras Tripolis": "Αστέρας Τρίπολης",
    "Atromitos": "Ατρόμητος", "Panionios": "Πανιώνιος", "Xanthi": "Ξάνθη", "Skoda Xanthi": "Ξάνθη",
    "Larisa": "ΑΕΛ", "AE Lárissa": "ΑΕΛ", "AEL": "ΑΕΛ", "Larissa": "ΑΕΛ", "Levadeiakos": "Λεβαδειακός",
    "Levadiakos": "Λεβαδειακός", "Panetolikos": "Παναιτωλικός", "Lamia": "Λαμία", "Volos NFC": "Βόλος",
    "Giannina": "ΠΑΣ Γιάννινα", "PAS Giannina": "ΠΑΣ Γιάννινα", "Ionikos": "Ιωνικός", "Iraklis": "Ηρακλής",
    "Kalamata": "Καλαμάτα", "Ergotelis": "Εργοτέλης", "Kerkyra": "Κέρκυρα", "Veria": "Βέροια",
    "Platanias": "Πλατανιάς", "Panserraikos": "Πανσερραϊκός", "Apollon": "Απόλλων Σμύρνης",
    "Apollon Smyrnis": "Απόλλων Σμύρνης", "GS Kallithea": "Καλλιθέα", "Kallithea": "Καλλιθέα",
    "Egaleo": "Αιγάλεω", "Athinaikos": "Αθηναϊκός", "Ethnikos Asteras": "Εθνικός Αστέρας",
    "Eth Asteras": "Εθνικός Αστέρας", "Kavala": "Καβάλα", "Kastoria": "Καστοριά", "Akratitos": "Ακράτητος",
    "Proodeftiki": "Προοδευτική", "Paniliakos": "Πανηλειακός", "Doxa Drama": "Δόξα Δράμας",
    "AE Kifisia": "Κηφισιά", "Kifisia": "Κηφισιά", "Chania": "Χανιά", "Thrasyvoulos": "Θρασύβουλος",
    "AE Kifisias": "Κηφισιά", "Doxa": "Δόξα Δράμας", "Doxa Dramas": "Δόξα Δράμας", "Eleysina": "Πανελευσινιακός",
    "Ethnikos Piraeus": "Εθνικός Πειραιά", "Heracles": "Ηρακλής", "Kalamaria": "Απόλλων Καλαμαριάς", "Kallonis": "Καλλονή",
    "Panionios GSS": "Πανιώνιος", "Panthrakikos": "Πανθρακικός", "Proodeytiki": "Προοδευτική", "Veroia": "Βέροια",
    "Xanthi FC": "Ξάνθη", "Aris Thessaloniki": "Άρης", "PAOK Thessaloniki": "ΠΑΟΚ", "AEK Athens FC": "ΑΕΚ",
    "Chalkidona": "Χαλκηδόνα", "Volos": "Βόλος", "Yiannina": "ΠΑΣ Γιάννινα", "Agrotikos Asteras": "Αγροτικός Αστέρας", "Edessaikos": "Εδεσσαϊκός", "Naoussa": "Νάουσα",
    "Trikala": "Τρίκαλα", "Kalithea": "Καλλιθέα", "Panahaiki": "Παναχαϊκή", "Panachaiki": "Παναχαϊκή",
    "Panegialios": "Πανιγιάλειος", "Ethnikos": "Εθνικός Πειραιά", "Olympiakos Volou": "Ολυμπιακός Βόλου",
    "Atromitos Athens": "Ατρόμητος", "Asteras Tripoli": "Αστέρας Τρίπολης",
}
def gr(n):
    n = n.strip()
    return NAME.get(n, n)


NAME.update({"Olympiakos": "Ολυμπιακός", "Olympiakos Piraeus": "Ολυμπιακός", "Volos NFC": "Βόλος", "Iraklis 1908": "Ηρακλής",
             "OFI Crete": "ΟΦΗ", "Kifisia": "Κηφισιά", "AE Kifisia": "Κηφισιά", "Aris Thessaloniki": "Άρης", "Panaitolikos": "Παναιτωλικός",
             "Levadiakos": "Λεβαδειακός", "Asteras Tripoli": "Αστέρας Τρίπολης", "Larissa": "ΑΕΛ", "AEL Larissa": "ΑΕΛ", "Kalamata": "Καλαμάτα",
             "Panserraikos": "Πανσερραϊκός", "Athens Kallithea": "Καλλιθέα", "Lamia": "Λαμία", "Giannina": "ΠΑΣ Γιάννινα", "Atromitos": "Ατρόμητος",
             "Marko": "Μαρκό", "Chania": "Χανιά", "Niki Volos": "Νίκη Βόλου", "Panionios": "Πανιώνιος",
             "Kalloni": "Καλλονή", "AEL Kalloni": "Καλλονή", "Apollon Smirnis": "Απόλλων Σμύρνης", "Apollon Smyrni": "Απόλλων Σμύρνης",
             "Iraklis Thessaloniki": "Ηρακλής", "Panthrakikos FC": "Πανθρακικός", "Ionikos Nikaias": "Ιωνικός", "Ionikos Nikea": "Ιωνικός"})

def is_oly(n):
    n = (n or "").strip()
    return n.startswith(("Olympiakos", "Olympiacos")) and "Volou" not in n and "B" != n.split()[-1]
