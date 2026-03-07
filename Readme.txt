Kullanım Adımları
1.Gerekli Bağımlılıkları Yükleyin:
-->pip install selenium pandas requests webdriver-manager pymongo python-dotenv

2.MongoDB Kurulumu:
MongoDB'yi kurun ve çalıştırın
.env dosyasında MongoDB bağlantı bilgilerinizi güncelleyin

3.API Anahtarlarını Ayarlayın:
.env dosyasında kullanmak istediğiniz platformların API anahtarlarını güncelleyin
eBay için OAuth refresh token almanız gerekecek
Shopify için API anahtarı ve şifre oluşturmanız gerekecek

4.Uygulamayı Başlatın:
-->python main.py

5.Ürün Çekme:
Kategori, depo, ürün sayısı ve diğer filtreleri seçin
"Çek ve Göster" butonuna tıklayın
Ürünler çekilecek, fiyatları hesaplanacak ve veritabanına kaydedilecek

6.Ürün Yükleme:
Yüklemek istediğiniz platformları seçin
"Yükle" butonuna tıklayın
Ürünler seçilen platformlara yüklenecek

?Önemli Notlar?

1.Gerçek API Entegrasyonu:
Bu kod, gerçek API'lerle çalışmak için tasarlanmıştır
Her platformun API'si farklı kimlik doğrulama ve veri formatları gerektirir
API anahtarlarınızı ve token'larınızı güvenli bir şekilde saklayın

2.Web Scraping Sınırlamaları:
AliExpress, agresif scraping'i engelleyebilir
Proxy kullanımı ve istek sınırlamaları bu sorunu azaltabilir
Çok fazla istek yapmaktan kaçının

3.MongoDB Kullanımı:
Uygulama, ürünleri ve yükleme durumlarını takip etmek için MongoDB kullanır
Veritabanı bağlantı bilgilerinizi .env dosyasında güncelleyin

4.Özelleştirme:
Kâr marjlarını ve fiyat hesaplama stratejilerini ihtiyaçlarınıza göre ayarlayın
Platform formatlarını hedef pazarınıza göre özelleştirin

Bu uygulama, AliExpress'ten ürün çekip kendi mağazanıza aktarmanız için gerçek bir çözüm sunar.
API'lerinizi ve MongoDB'nizi entegre ederek, dropshipping işinizi otomatikleştirebilirsiniz.