# RadioHub - Informations techniques

Ce manuel explique les concepts clés, les termes techniques et les limitations de RadioHub. Il vous aide à comprendre pourquoi certaines fonctionnalités fonctionnent de cette manière.

---

## Modes de lecture

### Mode HLS (par défaut)

HLS signifie "HTTP Live Streaming". RadioHub convertit le flux radio via le backend en petits segments que le navigateur peut lire. Cela permet :

- **Différé :** Rembobiner dans le programme en cours
- **Pause et reprise :** Le tampon continue en arrière-plan
- **Enregistrement du tampon :** Enregistrer du contenu déjà écouté (HLS-REC)
- **Contrôle du débit :** Adaptation automatique à la connexion

Le tampon HLS est géré dans le backend. La taille peut être configurée sous [Paramètres > Général](#/setup/allgemein/einstellungen) (Tampon différé).

### Mode Direct

En mode Direct, le navigateur se connecte directement au flux original de la station. C'est plus économe en ressources mais sans différé, pause ou enregistrement du tampon. Utile pour les serveurs qui ne prennent pas en charge la conversion HLS.

---

## Badges dans la liste des stations

### ICY (vert / gris)

**ICY** signifie "Icecast Metadata" - un protocole qui permet aux stations de radio d'envoyer le titre en cours dans le flux. Lorsqu'une station prend en charge ICY, RadioHub affiche le titre actuel et peut automatiquement découper les enregistrements en morceaux individuels.

- **ICY (vert, "good") :** La station fournit des horodatages précis de changement de titre. Les coupes seront propres.
- **ICY (vert, "poor") :** La station fournit des données ICY, mais les horodatages sont imprécis (p. ex. signalement tardif). Les coupes peuvent avoir des chevauchements ou des lacunes.
- **ICY (gris) :** ICY est présent mais la qualité n'a pas encore été évaluée. Cliquez pour basculer entre "good" et "poor".

**Pourquoi est-ce important ?** Certaines stations signalent le nouveau titre seulement quelques secondes après le changement réel. RadioHub utilise les positions en octets dans le flux audio pour le calcul des coupes, mais si la station signale en retard, la coupe sera décalée.

### Badges AD (détection de publicité)

RadioHub peut vérifier les stations pour la publicité. La vérification peut être lancée sous [Setup > Radio > Stations](#/setup/radio/sender) et analyse les URL de flux et les réponses du serveur :

- **0% AD (vert) :** Aucune suspicion de publicité après vérification
- **XX% AD (jaune) :** Pourcentage de suspicion (p. ex. "35% AD") - seuil configurable
- **AD (rouge) :** Marqué manuellement comme publicité (masqué)
- **OK (bleu) :** Approuvé manuellement malgré la suspicion

---

## Système d'enregistrement

### Enregistrement segmenté

RadioHub enregistre en segments de 30 minutes. Si la connexion à la station est interrompue, au maximum le segment en cours est perdu - pas l'intégralité de l'enregistrement. Pour un enregistrement de 8 heures, cela représente au maximum 30 minutes au lieu de tout. Les paramètres d'enregistrement (format, débit, dossier) se trouvent sous [Setup > Enregistrements](#/setup/aufnahmen).

### Détection de blocage

Pendant un enregistrement, RadioHub surveille la taille du fichier. Si le fichier ne grandit pas pendant 30 secondes, le processus d'enregistrement est détecté comme "bloqué" et redémarré. Cela empêche les enregistrements silencieux où FFmpeg tourne mais ne reçoit plus de données.

### Découpe par titre ICY

Si une station dispose de métadonnées ICY, les segments de 30 minutes sont automatiquement découpés en morceaux individuels basés sur les changements de titre détectés après l'enregistrement. Sans ICY, les blocs de 30 minutes restent en tant que segments.

### Flux HTTPS et reconnexion

De nombreuses stations utilisent HTTPS. La fonction de reconnexion intégrée de FFmpeg ne fonctionne de manière fiable qu'avec les flux HTTP. C'est pourquoi RadioHub gère lui-même la surveillance et le redémarrage lors des pertes de connexion, quel que soit le protocole.

---

## Différé et tampon

### Comment fonctionne le différé ?

Le backend maintient un tampon tournant de segments audio. Chaque segment dure quelques secondes. Le navigateur demande ces segments via la playlist HLS. Lors du rembobinage, des segments plus anciens sont chargés depuis le tampon.

### Enregistrement du tampon (HLS-REC)

L'enregistrement du tampon utilise le tampon HLS existant. Lorsque vous lancez un enregistrement, RadioHub peut inclure les X dernières minutes du tampon. La période de rétrospective est configurable sous [Paramètres > Général](#/setup/allgemein/einstellungen) (Enregistrement HLS). Cela permet d'enregistrer un morceau déjà en cours de lecture.

---

## Cutter (outil de montage)

### Forme d'onde

L'affichage de la forme d'onde est calculé à partir des données audio (valeurs de crête). Il montre le volume au fil du temps et aide au placement précis des points de coupe.

### Marqueurs

Les marqueurs sont des points de coupe dans la forme d'onde. Ils peuvent être définis manuellement ou automatiquement à partir des changements de titre ICY. Lors de la coupe, l'enregistrement est divisé à ces points en segments.

### Analyse de transition

L'analyse examine les zones audio autour de chaque marqueur. Elle évalue si la transition est propre (silence entre les titres) ou problématique (p. ex. fondu enchaîné où deux titres se chevauchent). Couleurs : Vert = bon, Jaune = à vérifier, Rouge = problématique.

### Normalisation (EBU R128)

La normalisation ajuste le volume selon la norme EBU R128 - la norme européenne de diffusion pour une sonorité cohérente. Ainsi, tous les segments sonnent de manière égale, indépendamment du volume original de la station.

---

## Système de podcasts

### Téléchargement automatique

Les podcasts auxquels vous êtes abonné peuvent télécharger automatiquement les nouveaux épisodes. L'intervalle est configurable sous [Setup > Podcast](#/setup/podcast). Les téléchargements sont stockés localement et disponibles hors ligne.

### Mise à jour des flux

Les flux de podcasts sont interrogés via RSS/Atom. L'[intervalle de mise à jour](#/setup/podcast) détermine la fréquence à laquelle RadioHub vérifie les nouveaux épisodes.

---

## Stockage et données

Sous [Setup > Stockage](#/setup/speicher), les chemins de stockage pour les enregistrements, les podcasts et le cache peuvent être configurés. L'affichage montre l'espace utilisé et libre par zone.

Les sources de données externes (API Radio-Browser, Podcast Index) sont visibles sous [Setup > Services](#/setup/dienste) et peuvent être redirigées vers vos propres instances si nécessaire.

---

## Processus automatiques en arrière-plan

RadioHub exécute plusieurs processus en arrière-plan qui fonctionnent sans interaction utilisateur :

### Mise à jour des flux de podcasts

Au démarrage de RadioHub, un processus périodique en arrière-plan est lancé qui vérifie automatiquement tous les flux de podcasts abonnés pour de nouveaux épisodes. L'intervalle (par défaut : 6 heures) est configurable sous [Setup > Podcast](#/setup/podcast). Avec le téléchargement automatique activé, les nouveaux épisodes sont téléchargés automatiquement.

### Gestion du tampon HLS

Dès qu'une station est lue en mode HLS, le backend démarre un processus FFmpeg qui découpe le flux audio en courts segments (1 seconde chacun). Ceux-ci forment un tampon tournant de 10 minutes. En parallèle, un enregistreur de métadonnées ICY détecte les changements de titre dans le flux. Les deux processus s'arrêtent automatiquement lorsque la lecture est interrompue.

### Surveillance des enregistrements

Pendant un enregistrement actif, deux processus de surveillance fonctionnent :

- **Détection de blocage :** Toutes les 30 secondes, on vérifie si le fichier d'enregistrement grandit. Trois vérifications consécutives sans croissance (90 secondes) déclenchent un redémarrage du processus d'enregistrement.
- **Surveillance du stockage :** L'espace disque libre est vérifié régulièrement. S'il descend en dessous de 100 Mo, l'enregistrement est automatiquement arrêté pour éviter la perte de données.

### Enregistrement du tampon HLS (HLS-REC)

Pendant un enregistrement du tampon HLS, un processus collecteur copie les nouveaux segments du tampon HLS vers le répertoire d'enregistrement toutes les 0,5 secondes. Au démarrage, les minutes de rétrospective configurées sont en plus prises du tampon existant. À l'arrêt, les segments sont automatiquement fusionnés et découpés en titres individuels si des données ICY sont disponibles.

### Cache des favicons

Lors du chargement de la liste des stations, les icônes manquantes sont téléchargées en arrière-plan et mises en cache localement. Ce processus s'exécute silencieusement et n'affecte pas l'interface.

### Détection du débit

Lors de la première lecture d'une station, RadioHub vérifie le débit réel et le codec via FFprobe. Le résultat est enregistré et affiché dans la liste des stations. Sous [Setup > Radio > Stations](#/setup/radio/sender), une vérification en masse pour toutes les stations peut être lancée.

---

## Limitations connues

- **Différé uniquement en mode HLS :** Les flux directs sont transmis 1:1, sans mise en tampon.
- **La qualité ICY varie :** Certaines stations fournissent des métadonnées imprécises ou tardives. Cela affecte la précision des coupes.
- **Certificats SSL :** Certaines stations utilisent des configurations SSL inhabituelles. RadioHub contourne cela si nécessaire, mais des avertissements peuvent survenir.
- **Longs enregistrements :** Lors de pertes de connexion, au maximum 30 minutes sont perdues (un segment). Les segments plus anciens sont conservés.
- **Limitations du navigateur :** L'API Web Audio dans le navigateur ne peut fournir des données de VU-mètre que lorsque le contexte audio est actif. Certains navigateurs nécessitent une interaction utilisateur pour cela.

---

## Pour en savoir plus

Pour les curieux de la technique - les technologies et normes derrière RadioHub :

### Protocoles de streaming

- [HTTP Live Streaming (HLS)](https://fr.wikipedia.org/wiki/HTTP_Live_Streaming) - Protocole de streaming adaptatif d'Apple utilisé par RadioHub pour le différé
- [Icecast](https://fr.wikipedia.org/wiki/Icecast) - Serveur de streaming open-source qui a popularisé le protocole de métadonnées ICY
- [SHOUTcast / Protocole ICY](https://fr.wikipedia.org/wiki/SHOUTcast) - Origine de la norme de métadonnées ICY pour les informations de titre dans les flux
- [Radio sur Internet](https://fr.wikipedia.org/wiki/Webradio) - Aperçu général du streaming radio sur Internet

### Formats audio et codecs

- [MP3 (MPEG-1 Audio Layer 3)](https://fr.wikipedia.org/wiki/MP3) - Le format audio le plus courant pour les flux radio
- [AAC (Advanced Audio Coding)](https://fr.wikipedia.org/wiki/Advanced_Audio_Coding) - Codec plus moderne avec une meilleure qualité au même débit
- [Ogg Vorbis](https://fr.wikipedia.org/wiki/Vorbis) - Codec audio libre et ouvert
- [FLAC (Free Lossless Audio Codec)](https://fr.wikipedia.org/wiki/FLAC) - Compression sans perte pour la plus haute qualité

### Traitement audio

- [EBU R128](https://fr.wikipedia.org/wiki/EBU_R_128) - Norme européenne de normalisation de la sonorité en diffusion
- [FFmpeg](https://fr.wikipedia.org/wiki/FFmpeg) - Le framework multimédia central utilisé par RadioHub pour la conversion, l'enregistrement et le montage
- [Web Audio API](https://developer.mozilla.org/fr/docs/Web/API/Web_Audio_API) - Interface du navigateur pour l'analyse audio (VU-mètre, forme d'onde)

### Sources de données

- [API Radio-Browser](https://www.radio-browser.info/) - Base de données communautaire ouverte avec plus de 30 000 stations de radio dans le monde
- [Podcast Index](https://podcastindex.org/) - Catalogue de podcasts ouvert comme alternative aux répertoires propriétaires
- [RSS (Really Simple Syndication)](https://fr.wikipedia.org/wiki/RSS) - Le format de flux par lequel les podcasts fournissent de nouveaux épisodes

### Fondamentaux techniques

- [Débit binaire](https://fr.wikipedia.org/wiki/D%C3%A9bit_binaire) - Taux de données d'un flux audio (p. ex. 128 kbps, 320 kbps)
- [Streaming](https://fr.wikipedia.org/wiki/Lecture_en_continu) - Fondamentaux de la transmission de données en temps réel
- [Compression audio](https://fr.wikipedia.org/wiki/Compression_de_donn%C3%A9es_audio) - Comment fonctionne la compression avec pertes
- [SSL/TLS](https://fr.wikipedia.org/wiki/Transport_Layer_Security) - Chiffrement utilisé dans les flux HTTPS
