# RadioHub - Teknik Bilgiler

Bu kılavuz, RadioHub'ın temel kavramlarını, teknik terimlerini ve sınırlamalarını açıklar. Belirli özelliklerin neden bu şekilde çalıştığını anlamanıza yardımcı olur.

---

## Oynatma Modları

### HLS Modu (Varsayılan)

HLS, "HTTP Live Streaming" anlamına gelir. RadioHub, radyo akışını backend üzerinden tarayıcının oynatabildiği küçük segmentlere dönüştürür. Bu sayede:

- **Zaman kaydırma:** Devam eden program içinde geri sarma
- **Duraklatma ve devam ettirme:** Tampon arka planda devam eder
- **Tampon kaydı:** Daha önce dinlenen içeriği kaydetme (HLS-REC)
- **Bitrate kontrolü:** Bağlantıya otomatik uyarlama

HLS tamponu backend'de tutulur. Boyutu [Ayarlar > Genel](#/setup/allgemein/einstellungen) altında yapılandırılabilir (Zaman Kaydırma Tamponu).

### Direct Modu

Direct modunda tarayıcı, istasyonun orijinal akışına doğrudan bağlanır. Bu daha az kaynak tüketir ancak zaman kaydırma, duraklatma veya tampon kaydı olmadan. HLS dönüştürmesini desteklemeyen sunucular için kullanışlıdır.

---

## İstasyon Listesindeki Rozetler

### ICY (yeşil / gri)

**ICY**, "Icecast Metadata" anlamına gelir - radyo istasyonlarının akış içinde geçerli başlığı göndermesine olanak tanıyan bir protokol. Bir istasyon ICY desteklediğinde, RadioHub geçerli başlığı görüntüler ve kayıtları otomatik olarak bireysel parçalara bölebilir.

- **ICY (yeşil, "iyi"):** İstasyon hassas başlık değişikliği zaman damgaları sağlar. Kesimler temiz olacaktır.
- **ICY (yeşil, "zayıf"):** İstasyon ICY verisi sağlar, ancak zaman damgaları hatalıdır (ör. geciken bildirimler). Kesimlerde örtüşmeler veya boşluklar olabilir.
- **ICY (gri):** ICY mevcut ancak kalitesi henüz değerlendirilmemiş. "İyi" ve "zayıf" arasında geçiş yapmak için tıklayın.

**Bu neden önemli?** Bazı istasyonlar yeni başlığı gerçek değişiklikten ancak birkaç saniye sonra bildirir. RadioHub, kesim hesaplaması için ses akışındaki bayt pozisyonlarını kullanır, ancak istasyon gecikmeli bildirirse kesim yanlış olur.

### AD Rozetleri (Reklam Tespiti)

RadioHub istasyonları reklamlara karşı kontrol edebilir. Kontrol [Ayarlar > Radyo > İstasyonlar](#/setup/radio/sender) altından başlatılabilir ve akış URL'lerini ve sunucu yanıtlarını analiz eder:

- **0% AD (yeşil):** Kontrolden sonra reklam şüphesi yok
- **XX% AD (sarı):** Yüzde şüphesi (ör. "35% AD") - eşik yapılandırılabilir
- **AD (kırmızı):** Manuel olarak reklam olarak işaretlenmiş (gizli)
- **OK (mavi):** Şüpheye rağmen manuel olarak onaylanmış

---

## Kayıt Sistemi

### Segmentli Kayıt

RadioHub 30 dakikalık segmentler halinde kaydeder. İstasyon bağlantısı koparsa, en fazla mevcut segment kaybolur - tüm kayıt değil. 8 saatlik bir kayıt için bu, her şey yerine en fazla 30 dakika demektir. Kayıt ayarları (format, bitrate, klasör) [Ayarlar > Kayıtlar](#/setup/aufnahmen) altındadır.

### Durma Tespiti

Bir kayıt sırasında RadioHub dosya boyutunu izler. Dosya 30 saniye boyunca büyümezse, kayıt işlemi "durmuş" olarak tespit edilir ve yeniden başlatılır. Bu, FFmpeg çalışıyor ancak artık veri almıyorken oluşan sessiz kayıtları önler.

### ICY Başlık Bölme

Bir istasyonun ICY metadatası varsa, 30 dakikalık segmentler kayıttan sonra tespit edilen başlık değişikliklerine göre otomatik olarak bireysel parçalara bölünür. ICY olmadan, 30 dakikalık bloklar segment olarak kalır.

### HTTPS Akışları ve Yeniden Bağlanma

Birçok istasyon HTTPS kullanır. FFmpeg'in yerleşik yeniden bağlanma işlevi yalnızca HTTP akışlarıyla güvenilir çalışır. Bu nedenle RadioHub, bağlantı koptuğunda izleme ve yeniden başlatma işlemini protokolden bağımsız olarak kendi yönetir.

---

## Zaman Kaydırma ve Tampon

### Zaman Kaydırma Nasıl Çalışır?

Backend, döner bir ses segmenti tamponu tutar. Her segment birkaç saniye uzunluğundadır. Tarayıcı bu segmentleri HLS oynatma listesi üzerinden ister. Geri sarıldığında, tampondan daha eski segmentler yüklenir.

### Tampon Kaydı (HLS-REC)

Tampon kaydı mevcut HLS tamponunu kullanır. Bir kayıt başlattığınızda, RadioHub tampondan son X dakikayı dahil edebilir. Geriye bakış süresi [Ayarlar > Genel](#/setup/allgemein/einstellungen) altında yapılandırılabilir (HLS Kaydı). Bu, halihazırda çalan bir parçanın kaydedilmesini sağlar.

---

## Cutter (Düzenleme Aracı)

### Dalga Formu

Dalga formu görüntüsü ses verilerinden (tepe değerler) hesaplanır. Zaman içindeki ses seviyesini gösterir ve kesim noktalarının hassas yerleştirilmesine yardımcı olur.

### İşaretçiler

İşaretçiler dalga formundaki kesim noktalarıdır. Manuel olarak veya ICY başlık değişikliklerinden otomatik olarak ayarlanabilir. Kesim sırasında kayıt bu noktalarda segmentlere bölünür.

### Geçiş Analizi

Analiz, her işaretçinin etrafındaki ses alanlarını inceler. Geçişin temiz (başlıklar arasında sessizlik) veya sorunlu (ör. iki başlığın örtüştüğü crossfade) olup olmadığını değerlendirir. Renkler: Yeşil = iyi, Sarı = kontrol et, Kırmızı = sorunlu.

### Normalizasyon (EBU R128)

Normalizasyon, ses seviyesini EBU R128 standardına - tutarlı ses yüksekliği için Avrupa yayın standardına - ayarlar. Böylece tüm segmentler, istasyonun orijinal ses seviyesinden bağımsız olarak eşit şekilde duyulur.

---

## Podcast Sistemi

### Otomatik İndirme

Abone olunan podcastlar yeni bölümleri otomatik olarak indirebilir. Aralık [Ayarlar > Podcast](#/setup/podcast) altında yapılandırılabilir. İndirmeler yerel olarak depolanır ve çevrimdışı kullanılabilir.

### Akış Güncellemesi

Podcast akışları RSS/Atom üzerinden sorgulanır. [Güncelleme aralığı](#/setup/podcast), RadioHub'ın yeni bölümleri ne sıklıkla kontrol ettiğini belirler.

---

## Depolama ve Veriler

[Ayarlar > Depolama](#/setup/speicher) altında kayıtlar, podcastlar ve önbellek için depolama yolları yapılandırılabilir. Ekran her bölge için kullanılan ve boş alanı gösterir.

Harici veri kaynakları (Radio-Browser API, Podcast Index) [Ayarlar > Hizmetler](#/setup/dienste) altında görünür ve gerektiğinde kendi örneklerinize yönlendirilebilir.

---

## Otomatik Arka Plan İşlemleri

RadioHub, kullanıcı etkileşimi olmadan çalışan birkaç arka plan işlemi yürütür:

### Podcast Akışı Güncellemesi

RadioHub başladığında, tüm abone olunan podcast akışlarını yeni bölümler için otomatik olarak kontrol eden periyodik bir arka plan işlemi başlatılır. Aralık (varsayılan: 6 saat) [Ayarlar > Podcast](#/setup/podcast) altında yapılandırılabilir. Otomatik indirme etkinleştirildiğinde, yeni bölümler otomatik olarak indirilir.

### HLS Tampon Yönetimi

Bir istasyon HLS modunda oynatılmaya başladığında, backend ses akışını kısa segmentlere (her biri 1 saniye) bölen bir FFmpeg işlemi başlatır. Bunlar 10 dakikalık döner bir tampon oluşturur. Paralel olarak, akıştaki başlık değişikliklerini tespit eden bir ICY metadata kaydedici çalışır. Her iki işlem de oynatma durdurulduğunda otomatik olarak sona erer.

### Kayıt İzleme

Aktif bir kayıt sırasında iki izleme işlemi çalışır:

- **Durma tespiti:** Her 30 saniyede kayıt dosyasının büyüyüp büyümediği kontrol edilir. Büyüme olmadan art arda üç kontrol (90 saniye) kayıt işleminin yeniden başlatılmasını tetikler.
- **Depolama izleme:** Boş disk alanı düzenli olarak kontrol edilir. 100 MB'ın altına düşerse, veri kaybını önlemek için kayıt otomatik olarak durdurulur.

### HLS Tampon Kaydı (HLS-REC)

Bir HLS tampon kaydı sırasında, bir toplayıcı işlem her 0,5 saniyede HLS tamponundan kayıt dizinine yeni segmentler kopyalar. Başlangıçta, yapılandırılmış geriye bakış dakikaları ek olarak mevcut tampondan alınır. Durdurmada, segmentler otomatik olarak birleştirilir ve ICY verisi mevcutsa bireysel başlıklara bölünür.

### Favicon Önbelleği

İstasyon listesi yüklenirken, eksik istasyon simgeleri arka planda indirilir ve yerel olarak önbelleğe alınır. Bu işlem sessizce çalışır ve arayüzü etkilemez.

### Bitrate Tespiti

Bir istasyon ilk kez oynatıldığında, RadioHub gerçek bitrate ve kodeki FFprobe ile kontrol eder. Sonuç kaydedilir ve istasyon listesinde gösterilir. [Ayarlar > Radyo > İstasyonlar](#/setup/radio/sender) altında tüm istasyonlar için toplu kontrol başlatılabilir.

---

## Bilinen Sınırlamalar

- **Zaman kaydırma yalnızca HLS modunda:** Direct akışlar tamponlama olmadan 1:1 aktarılır.
- **ICY kalitesi değişir:** Bazı istasyonlar hatalı veya geciken metadata sağlar. Bu, kesim hassasiyetini etkiler.
- **SSL sertifikaları:** Bazı istasyonlar alışılmadık SSL yapılandırmaları kullanır. RadioHub bunu gerektiğinde çözer, ancak uyarılar oluşabilir.
- **Uzun kayıtlar:** Bağlantı kopmalarında en fazla 30 dakika kaybolur (bir segment). Daha eski segmentler korunur.
- **Tarayıcı sınırlamaları:** Tarayıcıdaki Web Audio API, yalnızca ses bağlamı aktif olduğunda VU metre verisi sağlayabilir. Bazı tarayıcılar bunun için kullanıcı etkileşimi gerektirir.

---

## Ek Okuma

Teknik meraklılar için - RadioHub'ın arkasındaki teknolojiler ve standartlar:

### Akış Protokolleri

- [HTTP Live Streaming (HLS)](https://tr.wikipedia.org/wiki/HTTP_Live_Streaming) - RadioHub tarafından zaman kaydırma için kullanılan Apple'ın uyarlanabilir akış protokolü
- [Icecast](https://tr.wikipedia.org/wiki/Icecast) - ICY metadata protokolünü popülerleştiren açık kaynaklı akış sunucusu
- [SHOUTcast / ICY Protokolü](https://tr.wikipedia.org/wiki/SHOUTcast) - Akışlardaki başlık bilgisi için ICY metadata standardının kökeni
- [İnternet radyosu](https://tr.wikipedia.org/wiki/%C4%B0nternet_radyosu) - İnternette radyo akışının genel görünümü

### Ses Formatları ve Kodekler

- [MP3 (MPEG-1 Audio Layer 3)](https://tr.wikipedia.org/wiki/MP3) - Radyo akışları için en yaygın ses formatı
- [AAC (Advanced Audio Coding)](https://tr.wikipedia.org/wiki/AAC) - Aynı bitrate'de daha iyi kalite sunan daha modern kodek
- [Ogg Vorbis](https://tr.wikipedia.org/wiki/Vorbis) - Ücretsiz, açık ses kodeki
- [FLAC (Free Lossless Audio Codec)](https://tr.wikipedia.org/wiki/FLAC) - En yüksek kalite için kayıpsız sıkıştırma

### Ses İşleme

- [EBU R128](https://en.wikipedia.org/wiki/EBU_R_128) - Yayıncılıkta ses yüksekliği normalizasyonu için Avrupa standardı
- [FFmpeg](https://tr.wikipedia.org/wiki/FFmpeg) - RadioHub tarafından dönüştürme, kayıt ve kesim için kullanılan merkezi multimedya framework'ü
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API) - Ses analizi için tarayıcı arayüzü (VU metre, dalga formu)

### Veri Kaynakları

- [Radio-Browser API](https://www.radio-browser.info/) - Dünya genelinde 30.000'den fazla radyo istasyonu ile açık topluluk veritabanı
- [Podcast Index](https://podcastindex.org/) - Tescilli dizinlere alternatif olarak açık podcast kataloğu
- [RSS (Really Simple Syndication)](https://tr.wikipedia.org/wiki/RSS) - Podcastların yeni bölümler sunduğu akış formatı

### Teknik Temeller

- [Bitrate](https://tr.wikipedia.org/wiki/Bit_h%C4%B1z%C4%B1) - Bir ses akışının veri hızı (ör. 128 kbps, 320 kbps)
- [Streaming media](https://tr.wikipedia.org/wiki/Ak%C4%B1%C5%9F_ortam%C4%B1) - Gerçek zamanlı veri iletiminin temelleri
- [Ses veri sıkıştırma](https://en.wikipedia.org/wiki/Audio_coding_format) - Kayıplı sıkıştırma nasıl çalışır
- [SSL/TLS](https://tr.wikipedia.org/wiki/Transport_Layer_Security) - HTTPS akışlarında kullanılan şifreleme
