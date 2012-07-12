import urllib
import urlparse
import re
import os
import threading

TORRENTS_FOLDER = "torrents"
ERROR_FOLDER = "tests"
TESTING = False
LOGGING_LEVEL = 0

class TorrentSiteDownloaderException(Exception):pass
class TorrentSiteDownloaderCantDownload(TorrentSiteDownloaderException):pass
class TorrentSiteDownloaderServerError(TorrentSiteDownloaderException):pass
class TorrentSiteDownloaderInvalidPage(TorrentSiteDownloaderException):pass
class TorrentSiteDownloaderInvalidTorrent(TorrentSiteDownloaderException):pass

def urlread(url):
    try:
        return urllib.urlopen(url).read()
    except:
        Logger("Server Error: %s" % (url,), 10)
        raise TorrentSiteDownloaderServerError()
    
def urlregexp(url, regexp_obj):
    return regexp_obj.findall(urlread(url))
    
def urlmagnet(url):
    Logger("Magnet: %s" % (url,), 1)
    
    if TESTING:
        Logger("Assume opening magnet", 0)
    else:
        os.startfile(url)
    



def urltorrent(url, local_torrent_path = None):
    Logger("Torrent: %s" % (url,), 1)
    if local_torrent_path is None:
        local_torrent_path = urllib.unquote(os.path.basename(url))
    if not local_torrent_path.endswith(".torrent"):
        local_torrent_path += ".torrent"

    local_torrent_path = os.path.join(TORRENTS_FOLDER, local_torrent_path)
    
    try:
        local_torrent_path, _ = urllib.urlretrieve(url, local_torrent_path) 
    except IOError:
        Logger("Cannot write to file %s from url %s" % (local_torrent_path, url,), 10)
        raise TorrentSiteDownloaderInvalidTorrent()

    # test the torrent file
    if not open(local_torrent_path, "rb").read().startswith("d8:announce"):
        raise TorrentSiteDownloaderInvalidTorrent()
        
    if TESTING:
        Logger("Assume opening %s" % (local_torrent_path,), 0)
    else:
        os.startfile(local_torrent_path)
        
class BaseLogger(object):
    def __init__(self, level = 0):
        super(BaseLogger, self).__init__()
        self._log_level = 0
        
    def set_level(self, level):
        self._log_level = level
        
class FileLogger(BaseLogger):
    def __init__(self, filename, level = 0):
        super(FileLogger, self).__init__(level)
        self._file = open(filename, "wt")
        
    def __call__(self, msg, level = 10):
        if level >= self._log_level:
            self._file.write(msg + "\n")
            self._file.flush()

class ScreenLogger(BaseLogger):
    def __init__(self, level = 0):
        super(ScreenLogger, self).__init__(level)
        
    def __call__(self, msg, level = 10):
        if level >= self._log_level:
            print msg
                    
class Logger(object):
    def __init__(self):
        super(Logger, self).__init__()
        self._loggers = []
        
    def add_logger(self, logger):
        self._loggers.append(logger)
        
    def __call__(self, msg, level = 10):
        for logger in self._loggers:
            logger(msg, level)            
        
    def log_url(self, url):
        open(os.path.join(ERROR_FOLDER, urlparse.urlsplit(url)[1] + "_errorpage.html"), "wt").write(urlread(url))
        
Logger = Logger()
    


class TorrentSiteDownloaderList(object):
    def __init__(self):
        super(TorrentSiteDownloaderList, self).__init__()
        self._torrent_site_downloader_list = []
        
    def add_downloader(self, downloader):
        self._torrent_site_downloader_list.append(downloader)
    
    def download_torrent(self, url):
        handled = False
        error = False

        for torrent_site_downloader in self._torrent_site_downloader_list:
            try:
                torrent_site_downloader.download_torrent(url)
                handled = True
            except TorrentSiteDownloaderCantDownload:
                pass
            except TorrentSiteDownloaderException:
                error = True
                
        if not handled:
            if not error:
                Logger("Unknown Torrent Site: %s" % (url,))
            try:
                Logger.log_url(url)
            except TorrentSiteDownloaderServerError:
                pass
            
TorrentSiteDownloaderList = TorrentSiteDownloaderList()


class Torrentz(object):
    def __init__(self):
        super(Torrentz, self).__init__()
        
        self._regexp = re.compile("\<dl\>\<dt\>\<a\x20href=\"(.*?)\"\x20rel=\"e\"\>.*?\</dl\>")
        
    def download_torrent(self, url):

        if not url.startswith("http://www.torrentz.com/") and not url.startswith("http://torrentz.eu/"):
            raise TorrentSiteDownloaderCantDownload()

        regexp_results = urlregexp(url, self._regexp)
        threads = []
        for regexp_result in regexp_results:
            Logger("Starting %s" % (regexp_result, ))
            thread = threading.Thread(target = TorrentSiteDownloaderList.download_torrent, args = (regexp_result,))
            thread.start()
            threads.append(thread)
                
        for thread in threads:
            thread.join()
        Logger("Done %s" % (url,))

class ThePirateBay(object):
    def __init__(self):
        super(ThePirateBay, self).__init__()
        self._torrent_regexp = re.compile("\<a\x20href=\"(.*)\"\x20title=\".*\"\>.*?\</a\>\x20\(")
        
        self._magnet_regexp = re.compile("\'\x20href=\"(.*?)\"")
        
        self._regexp = self._magnet_regexp
        
    def download_torrent(self, url):
        if not url.startswith("http://thepiratebay.org/") or not url.startswith("http://thepiratebay.se/torrent/"):
            raise TorrentSiteDownloaderCantDownload()
        Logger("Find torrent link in pitatebay")
        regexp_results = urlregexp(url, self._regexp)

        if len(regexp_results) != 2 or regexp_results[0] != regexp_results[1]:
            raise TorrentSiteDownloaderInvalidPage()
        
        urlmagnet(regexp_results[0])
        
class BTJunkie(object):
    def __init__(self):
        super(BTJunkie, self).__init__()
        self._torrent_regexp = re.compile("\<a\x20href=\"(.*?)\"\x20rel=\"nofollow\"\x20class=\"blocked_black\"\>")
        
        self._magnet_regexp = re.compile("\<a\x20href=\"(.*)\"\x20title=\"Magnet\x20Link\">")
        
        self._regexp = self._magnet_regexp
        
    def download_torrent(self, url):
        if not url.startswith("http://btjunkie.org/"):
            raise TorrentSiteDownloaderCantDownload()
            
        regexp_results = urlregexp(url, self._regexp)

        if len(regexp_results) != 1:
            raise TorrentSiteDownloaderInvalidPage()
        
        urlmagnet(regexp_results[0])
        
class TorrentHound(object):
    def __init__(self):
        super(TorrentHound, self).__init__()
        self._regexp = re.compile("\<a\x20rel=\"nofollow\"\x20href=\"(.*?)\".*\>")
        
    def download_torrent(self, url):
        if not url.startswith("http://www.torrenthound.com/"):
            raise TorrentSiteDownloaderCantDownload()
            
        regexp_results = urlregexp(url, self._regexp)

        if len(regexp_results) != 2:
            raise TorrentSiteDownloaderInvalidPage()

        urltorrent("http://www.torrenthound.com" + regexp_results[0])

class TorrentBIT(object):
    def __init__(self):
        super(TorrentBIT, self).__init__()
        self._regexp = re.compile("\<a\x20rel=\"nofollow\"\x20onclick=\".*?\"\x20href=\"(.*?)\"\x20title=\"Download\x20torrent\"\>")
        
    def download_torrent(self, url):
        if not url.startswith("http://www.torrentbit.nl/"):
            raise TorrentSiteDownloaderCantDownload()
            
        regexp_results = urlregexp(url, self._regexp)

        if len(regexp_results) != 2 or regexp_results[0] != regexp_results[1]:
            raise TorrentSiteDownloaderInvalidPage()        
        torrent = "http://www.torrentbit.nl" + regexp_results[0]

        urltorrent(torrent)
        
class NewTorrents(object):
    def __init__(self):
        super(NewTorrents, self).__init__()
        self._regexp = re.compile("\<a\x20href=\"(.*?)\".*\><b>")
        self._name_regexp = re.compile(".*down.php\?id=(\d*).*")
        
    def download_torrent(self, url):
        if not url.startswith("http://www.newtorrents.info/"):
            raise TorrentSiteDownloaderCantDownload()
            
        regexp_results = urlregexp(url, self._regexp)

        if len(regexp_results) != 1:
            raise TorrentSiteDownloaderInvalidPage()
        torrent = regexp_results[0]

        name_results = self._name_regexp.findall(torrent)
        if len(name_results) != 1:
            raise TorrentSiteDownloaderInvalidPage()
        torrent_name = urllib.unquote(name_results[0]) + ".torrent"
        
        urltorrent(torrent, torrent_name)
        
class BTMon(object):
    def __init__(self):
        super(BTMon, self).__init__()
        self._regexp = re.compile("\<div\x20class=\"dwnl\"\><a\x20href=\"(.*)\"\x20class=\"dwn_tor\"\>")
        
    def download_torrent(self, url):
        if not url.startswith("http://www.btmon.com/"):
            raise TorrentSiteDownloaderCantDownload()
            
        regexp_results = urlregexp(url, self._regexp)

        if len(regexp_results) != 1:
            raise TorrentSiteDownloaderInvalidPage()        
        torrent = "http://www.btmon.com" + regexp_results[0]

        urltorrent(torrent)
            

class ExtraTorrent(object):
    def __init__(self):
        super(ExtraTorrent, self).__init__()
        self._regexp = re.compile("\<a\x20href=\"(.*)\"\x20title=\"Download\x20Torrent")
        
    def download_torrent(self, url):
        if not url.startswith("http://extratorrent.com/torrent/"):
            raise TorrentSiteDownloaderCantDownload()
            
        regexp_results = urlregexp(url, self._regexp)

        if len(regexp_results) != 1:
            raise TorrentSiteDownloaderInvalidPage()        
        url = "http://extratorrent.com" + regexp_results[0]
        
        TorrentSiteDownloaderList.download_torrent(url)
        
class ExtraTorrentDownload(object):
    def __init__(self):
        super(ExtraTorrentDownload, self).__init__()
        self._regexp = re.compile("\<a\x20href=\"(.*?)\"\x20title=\"Download\x20Torrent:\x20.*?\"\>")
        
    def download_torrent(self, url):
        if not url.startswith("http://extratorrent.com/torrent_download/"):
            raise TorrentSiteDownloaderCantDownload()
            
        regexp_results = urlregexp(url, self._regexp)

        if len(regexp_results) != 1:
            raise TorrentSiteDownloaderInvalidPage()        
        torrent = "http://extratorrent.com" + regexp_results[0]
        
        urltorrent(torrent)
        
class YourBittorrent(object):
    def __init__(self):
        super(YourBittorrent, self).__init__()
        self._regexp = re.compile("\<a\x20href=\"(.*?)\"\x20class=\"dmaina\"\x20rel=\"nofollow\"\>")
        
    def download_torrent(self, url):
        if not url.startswith("http://www.yourbittorrent.com/"):
            raise TorrentSiteDownloaderCantDownload()
            
        regexp_results = urlregexp(url, self._regexp)

        if len(regexp_results) != 1:
            raise TorrentSiteDownloaderInvalidPage()        
        torrent = "http://www.yourbittorrent.com" + regexp_results[0]

        urltorrent(torrent)            

class H33T(object):
    def __init__(self):
        super(H33T, self).__init__()
        self._regexp = re.compile("\<a\x20class=\"det\"\x20href=\"(.*)\"><img")
        self._name_regexp = re.compile("f=(.*)")
        
    def download_torrent(self, url):
        if not url.startswith("http://www.h33t.com/"):
            raise TorrentSiteDownloaderCantDownload()
            
        regexp_results = urlregexp(url, self._regexp)

        if len(regexp_results) != 1:
            raise TorrentSiteDownloaderInvalidPage()        
        torrent = "http://www.h33t.com/" + regexp_results[0]

        name_results = self._name_regexp.findall(regexp_results[0])
        if len(name_results) != 1:
            raise TorrentSiteDownloaderInvalidPage()
        torrent_name = urllib.unquote(name_results[0]) + ".torrent"
        
        urltorrent(torrent, torrent_name)    
        
class AliveTorrents(object):
    def __init__(self):
        super(AliveTorrents, self).__init__()
        self._regexp = re.compile("\<a\x20rel=\"nofollow\"\x20href=\"(.*)\"\x20class=\"larger\">")
        
    def download_torrent(self, url):
        if not url.startswith("http://alivetorrents.com/"):
            raise TorrentSiteDownloaderCantDownload()
            
        regexp_results = urlregexp(url, self._regexp)

        if len(regexp_results) != 1:
            raise TorrentSiteDownloaderInvalidPage()        
        torrent = "http://alivetorrents.com" + regexp_results[0]
        
        urltorrent(torrent)    

class RARBG(object):
    def __init__(self):
        super(RARBG, self).__init__()
        self._regexp = re.compile("\<a\x20onmouseover=\".*?\"\x20onmouseout=\".*?\"\x20href=\"(.*?)\"\>")
        self._name_regexp = re.compile("f=(.*)")
        
    def download_torrent(self, url):
        if not url.startswith("http://rarbg.com/"):
            raise TorrentSiteDownloaderCantDownload()
            
        regexp_results = urlregexp(url, self._regexp)

        if len(regexp_results) != 1:
            raise TorrentSiteDownloaderInvalidPage()        
        torrent = "http://rarbg.com" + regexp_results[0]

        name_results = self._name_regexp.findall(regexp_results[0])
        if len(name_results) != 1:
            raise TorrentSiteDownloaderInvalidPage()
        torrent_name = urllib.unquote(name_results[0]) + ".torrent"
        
        urltorrent(torrent, torrent_name)    
        
class TorrentReactor(object):
    def __init__(self):
        super(TorrentReactor, self).__init__()
        self._regexp = re.compile("\<a\x20rel=\"nofollow\"\x20href=\"(.*?)\"\>\<img\x20src=\".*?b_dt\.gif\"\x20alt=\".*?\"\x20/\>\</a\>")
        self._name_regexp = re.compile(";name=(.*)")
        
    def download_torrent(self, url):
        if not url.startswith("http://www.torrentreactor.net/"):
            raise TorrentSiteDownloaderCantDownload()
            
        regexp_results = urlregexp(url, self._regexp)

        if len(regexp_results) != 2 or regexp_results[0] != regexp_results[1]:
            raise TorrentSiteDownloaderInvalidPage()        
        torrent = regexp_results[0]

        name_results = self._name_regexp.findall(regexp_results[0])
        if len(name_results) != 1:
            raise TorrentSiteDownloaderInvalidPage()
        torrent_name = urllib.unquote(name_results[0]) + ".torrent"
        
        urltorrent(torrent, torrent_name)        
        
class TorrentZAP(object):
    def __init__(self):
        super(TorrentZAP, self).__init__()
        self._regexp = re.compile("\<a\x20href=\"(.*?)\"\x20title=\"Download\x20with\x20magnet\x20link\"")
        
    def download_torrent(self, url):
        if not url.startswith("http://www.torrentzap.com/"):
            raise TorrentSiteDownloaderCantDownload()
            
        regexp_results = urlregexp(url, self._regexp)

        if len(regexp_results) != 2:
            raise TorrentSiteDownloaderInvalidPage()        
        torrent, magnet = regexp_results

        urlmagnet(magnet)    

class Fenopy(object):
    def __init__(self):
        super(Fenopy, self).__init__()
        self._regexp = re.compile("\<div\x20class=\"download\"\>\s*\<a\x20href=\"(.*?)\"\x20class=\"torrent\"\>")
        
    def download_torrent(self, url):
        
        if not url.startswith("http://fenopy.com/"):
            raise TorrentSiteDownloaderCantDownload()
            
        regexp_results = urlregexp(url, self._regexp)

        if len(regexp_results) != 1:
            raise TorrentSiteDownloaderInvalidPage()        
        torrent = regexp_results[0]

        urltorrent(torrent)    

class FenopyEU(object):
    def __init__(self):
        super(FenopyEU, self).__init__()
        self._regexp = re.compile("\<a\x20href=\"(.*?)\"\x20class=\"bt\x20ttip\"")
        
    def download_torrent(self, url):
        
        if not url.startswith("http://fenopy.eu/torrent/"):
            raise TorrentSiteDownloaderCantDownload()
            
        regexp_results = urlregexp(url, self._regexp)

        if len(regexp_results) != 1:
            raise TorrentSiteDownloaderInvalidPage()        
        magnet = regexp_results[0]

        urlmagnet(magnet) 

class SeedPeer(object):
    def __init__(self):
        super(SeedPeer, self).__init__()
        self._regexp = re.compile("or\x20use\x20the\x20<a\x20href=\"(.*?)\"\x20style=\"")
        
    def download_torrent(self, url):
        
        if not url.startswith("http://www.seedpeer.me/details/"):
            raise TorrentSiteDownloaderCantDownload()
            
        regexp_results = urlregexp(url, self._regexp)

        if len(regexp_results) != 1:
            raise TorrentSiteDownloaderInvalidPage()        
        magnet = regexp_results[0]

        urlmagnet(magnet) 


class BitTorrentAM(object):
    def __init__(self):
        super(BitTorrentAM, self).__init__()
        self._regexp = re.compile("\<form\x20action\x20=\x20\"(.*?)\"\x20method\x20=\x20\"get\"\x20target=\"_new\"\>\s*\<input\x20type=\"hidden\"\x20name=\"id\"\x20value=\"(\d*)\"\>\s*\<input\x20type=\"hidden\"\x20name=\"name\"\x20value=\"(.*)\"\>\s*")
        
    def download_torrent(self, url):
        if not url.lower().startswith("http://www.bittorrent.am/"):
            raise TorrentSiteDownloaderCantDownload()
            
        regexp_results = urlregexp(url, self._regexp)

        if len(regexp_results) != 3:
            raise TorrentSiteDownloaderInvalidPage()
        torrent = "http://www.BitTorrent.AM" + regexp_results[0] + "?id=" + regexp_results[1] + "&name=" + regexp_results[2]

        urltorrent(torrent)    
        
class BTChat(object):
    def __init__(self):
        super(BTChat, self).__init__()
        self._regexp = re.compile("\<td><a\x20href=\"(.*)\">")
        self._name_regexp = re.compile("\<td\x20colspan=\"2\"\x20class=\"aLeft\x20right\">(.*)</td>")
        
    def download_torrent(self, url):
        if not url.lower().startswith("http://www.bt-chat.com/"):
            raise TorrentSiteDownloaderCantDownload()
            
        url_data = urlread(url)
        
        regexp_results = self._regexp.findall(url_data)

        if len(regexp_results) != 1:
            raise TorrentSiteDownloaderInvalidPage()
        torrent = "http://www.bt-chat.com/" + regexp_results[0]
        
        name_results = self._name_regexp.findall(url_data)
        torrent_name = urllib.unquote(name_results[0]) + ".torrent"
        
        urltorrent(torrent, torrent_name)
        
class FullDLS(object):
    def __init__(self):
        super(FullDLS, self).__init__()
        self._torrent_regexp = re.compile("\<h1\><a\x20href=\"(.*?)\"\x20title=\".*\"\x20\x20rel=\"nofollow\"\>")
        self._magnet_regexp = re.compile("or\x20use\x20\<a\x20href=\"(.*?)\"")
        
    def download_torrent(self, url):
        if not url.lower().startswith("http://www.fulldls.com/"):
            raise TorrentSiteDownloaderCantDownload()
            
        #regexp_results = urlregexp(url, self._torrent_regexp)

        #if len(regexp_results) != 1:
        #    raise TorrentSiteDownloaderInvalidPage()
        #torrent = "http://www.fulldls.com/" + regexp_results[0]

        #urltorrent(torrent)    

        regexp_results = urlregexp(url, self._magnet_regexp)

        if len(regexp_results) != 1:
            raise TorrentSiteDownloaderInvalidPage()

        urlmagnet(regexp_results[0])    

class MoNova(object):
    def __init__(self):
        super(MoNova, self).__init__()
        self._torrent_regexp = re.compile("\<h2\>\<a\x20href=\"(.*?)\"\x20rel=\"nofollow\"\>")
        self._magnet_regexp = re.compile("\(\<a\x20href=\"(.*?)\"\>\<b\>Magnet\</b\>")
        
    def download_torrent(self, url):
        if not url.lower().startswith("http://www.monova.org/"):
            raise TorrentSiteDownloaderCantDownload()
            
        regexp_results = urlregexp(url, self._magnet_regexp)

        if len(regexp_results) != 1:
            raise TorrentSiteDownloaderInvalidPage()
        
        urlmagnet(regexp_results[0])
        
class SwarmTheHive(object):
    def __init__(self):
        super(SwarmTheHive, self).__init__()
        self._regexp = re.compile("\<a\x20href=\"(.*?)\"\>\<img.*?torrent_doc.png\"\>")
        self._name_regexp = re.compile("download.php\?id=(\d*)")
        
    def download_torrent(self, url):
        if not url.lower().startswith("http://www.swarmthehive.com/"):
            raise TorrentSiteDownloaderCantDownload()
            
        regexp_results = urlregexp(url, self._regexp)

        if len(regexp_results) != 1:
            raise TorrentSiteDownloaderInvalidPage()
        torrent = "http://www.swarmthehive.com/" + regexp_results[0]
        
        
        name_results = self._name_regexp.findall(regexp_results[0])
        if len(name_results) != 1:
            raise TorrentSiteDownloaderInvalidPage()
        torrent_name = urllib.unquote(name_results[0]) + ".torrent"
        
        urltorrent(torrent, torrent_name)
        
        
class Vertor(object):
    def __init__(self):
        super(Vertor, self).__init__()
        self._regexp = re.compile("\<a\x20href=\"(.*?)\"\x20class=\"downtorr\"\>")
        self._name_regexp = re.compile(";id=(\d*)")
    def download_torrent(self, url):
        if not url.lower().startswith("http://www.vertor.com/"):
            raise TorrentSiteDownloaderCantDownload()
            
        regexp_results = urlregexp(url, self._regexp)

        if len(regexp_results) != 1:
            raise TorrentSiteDownloaderInvalidPage()

        name_results = self._name_regexp.findall(regexp_results[0])
        if len(name_results) != 1:
            raise TorrentSiteDownloaderInvalidPage()
        torrent_name = urllib.unquote(name_results[0]) + ".torrent"
        
        urltorrent(regexp_results[0], torrent_name)
        
class KickAssTorrents(object):
    def __init__(self):
        super(KickAssTorrents, self).__init__()
        self._torrent_regexp = re.compile("\</a\>\s*\<a\x20title=\"Download\x20torrent\x20file\"\x20href=\"(.*?)\"\x20onclick=\".*\"\x20")
        
        self._magnet_regexp = re.compile("\<a\x20title=\"Torrent\x20magnet\x20link\"\x20href=\"(.*?)\"\x20onclick=\".*\"\x20class=\".*\"\>")
        
        self._regexp = self._magnet_regexp
        
    def download_torrent(self, url):
        if not url.startswith("http://www.kickasstorrents.com/"):
            raise TorrentSiteDownloaderCantDownload()
            
        regexp_results = urlregexp(url, self._regexp)

        if len(regexp_results) != 1:
            raise TorrentSiteDownloaderInvalidPage()
        
        urlmagnet(regexp_results[0])
        
class TorrentPortal(object):
    def __init__(self):
        super(TorrentPortal, self).__init__()
        self._regexp = re.compile("\<a\x20href=\"(.*?)\"\><h1")
        
    def download_torrent(self, url):
        if not url.startswith("http://torrentportal.com/"):
            raise TorrentSiteDownloaderCantDownload()
            
        regexp_results = urlregexp(url, self._regexp)

        if len(regexp_results) != 1:
            raise TorrentSiteDownloaderInvalidPage()
        torrent = "http://torrentportal.com" + regexp_results[0]
        
        urltorrent(torrent)
        
class Torrent1337X(object):
    def __init__(self):
        super(Torrent1337X, self).__init__()
        
        self._regexp = re.compile("\<a\x20href=\"(.*?)\"\x20class=\"magnet\"\x20title=\"Magnet\x20Link\"\x20alt=\"Magnet\x20Link\">Magnet\x20Link</a>")
        
    def download_torrent(self, url):
        if not url.startswith("http://1337x.org/"):
            raise TorrentSiteDownloaderCantDownload()
            
        regexp_results = urlregexp(url, self._regexp)

        if len(regexp_results) != 1:
            raise TorrentSiteDownloaderInvalidPage()
        urlmagnet(regexp_results[0])
        
class BitSnoop(object):
    def __init__(self):
        super(BitSnoop, self).__init__()
        
        self._regexp = re.compile("\<a href=\"(.*)\"\x20title=\"Magnet\x20Link\"")
        
    def download_torrent(self, url):
        if not url.startswith("http://bitsnoop.com/"):
            raise TorrentSiteDownloaderCantDownload()
            
        regexp_results = urlregexp(url, self._regexp)

        if len(regexp_results) != 1:
            raise TorrentSiteDownloaderInvalidPage()
        urlmagnet(regexp_results[0])
        
class TorrentDownloadsNet(object):
    def __init__(self):
        super(TorrentDownloadsNet, self).__init__()
        self._regexp = re.compile("")
        
    def download_torrent(self, url):
        
        if not url.startswith("http://torrentdownloads.net/"):
            raise TorrentSiteDownloaderCantDownload()
            
        regexp_results = urlregexp(url, self._regexp)

        if len(regexp_results) != 1:
            raise TorrentSiteDownloaderInvalidPage()        
        torrent = regexp_results[0]

        urltorrent(torrent)    

class TorrentsNet(object):
    def __init__(self):
        super(TorrentsNet, self).__init__()
        self._regexp = re.compile("\<a\x20href=\"(.*?)\"\x20class=btn2-download\>")
        
    def download_torrent(self, url):
        
        if not url.startswith("http://www.torrents.net/torrent/"):
            raise TorrentSiteDownloaderCantDownload()
            
        regexp_results = urlregexp(url, self._regexp)

        if len(regexp_results) != 1:
            raise TorrentSiteDownloaderInvalidPage()        
        magnet = regexp_results[0]

        urlmagnet(magnet)   

class TorrentFunk(object):
    def __init__(self):
        super(TorrentFunk, self).__init__()
        #self._regexp = re.compile("\<a\x20href=(.*)\>Download\x20Torrent\</a\>")
        self._regexp = re.compile("\>\<td\x20align=center\x20width=33%\>\<a\x20href=(.*?)\.torrent\x20rel=nofollow\>")
        
    def download_torrent(self, url):
        
        if not url.startswith("http://www.torrentfunk.com/"):
            raise TorrentSiteDownloaderCantDownload()
            
        regexp_results = urlregexp(url, self._regexp)

        if len(regexp_results) != 1:
            raise TorrentSiteDownloaderInvalidPage()        
        torrent = regexp_results[0]

        urltorrent("http://www.torrentfunk.com" + torrent + ".torrent")        

class TakeFM(object):
    def __init__(self):
        super(TakeFM, self).__init__()
        self._regexp = re.compile("\<a\x20href=\'(.*)\'\x20onclick=\"javascript:")
        
    def download_torrent(self, url):
        
        if not url.startswith("http://take.fm/"):
            raise TorrentSiteDownloaderCantDownload()
            
        regexp_results = urlregexp(url, self._regexp)

        if len(regexp_results) != 1:
            raise TorrentSiteDownloaderInvalidPage()        
        torrent = "http://take.fm/" + regexp_results[0]

        urltorrent(torrent)     
        
class LimeTorrents(object):
    def __init__(self):
        super(LimeTorrents, self).__init__()
        self._regexp = re.compile("\<p\><a\x20href=\"(.*)\"\x20rel=\"nofollow\"\>Download\x20torrent</a\>")
        
    def download_torrent(self, url):
        
        if not url.startswith("http://www.limetorrents.com/"):
            raise TorrentSiteDownloaderCantDownload()
            
        regexp_results = urlregexp(url, self._regexp)

        if len(regexp_results) != 1:
            raise TorrentSiteDownloaderInvalidPage()        
        torrent = "http://www.limetorrents.com/" + regexp_results[0]

        urltorrent(torrent)     
        
#class TorrentFunk(object):
#    def __init__(self):
#        super(TorrentFunk, self).__init__()
#        self._regexp = re.compile("\<a\x20href=(.*)>Download\x20Torrent</a>")
#        self._name_regexp = re.compile("var\x20gMessage=\'Download\x20(.*)\';var\x20gUrl")
#        
#    def download_torrent(self, url):
#        if not url.lower().startswith("http://www.torrentfunk.com/"):
#            raise TorrentSiteDownloaderCantDownload()
#            
#        url_data = urlread(url)
#        
#        regexp_results = self._regexp.findall(url_data)
#
#        if len(regexp_results) != 1:
#            raise TorrentSiteDownloaderInvalidPage()
#        torrent = "http://www.torrentfunk.com/" + regexp_results[0]
#        
#        name_results = self._name_regexp.findall(url_data)
#        torrent_name = urllib.unquote(name_results[0]) + ".torrent"
#        
#        urltorrent(torrent, torrent_name)
        
class Torrage(object):
    def __init__(self):
        super(Torrage, self).__init__()

    def download_torrent(self, url):
        if not url.startswith("http://torrage.com/"):
            raise TorrentSiteDownloaderCantDownload()
        
        urltorrent(url)
        
class TorCache(object):
    def __init__(self):
        super(TorCache, self).__init__()

    def download_torrent(self, url):
        if not url.startswith("http://torcache.com/"):
            raise TorrentSiteDownloaderCantDownload()
        
        urltorrent(url)
        
class ZoinkIT(object):
    def __init__(self):
        super(ZoinkIT, self).__init__()

    def download_torrent(self, url):
        if not url.startswith("http://zoink.it.com/"):
            raise TorrentSiteDownloaderCantDownload()
        
        urltorrent(url)
        
class TorrentzMagnet(object):
    def __init__(self):
        super(TorrentzMagnet, self).__init__()

    def download_torrent(self, url):
        if not url.startswith("magnet:?xt="):
            raise TorrentSiteDownloaderCantDownload()
        
        urlmagnet(url)
        
def LoadOpeners():
    TorrentSiteDownloaderList.add_downloader(Torrentz())
    
    TorrentSiteDownloaderList.add_downloader(ThePirateBay())
    TorrentSiteDownloaderList.add_downloader(BTJunkie())
    TorrentSiteDownloaderList.add_downloader(TorrentHound())
    TorrentSiteDownloaderList.add_downloader(TorrentBIT())
    TorrentSiteDownloaderList.add_downloader(NewTorrents())
    TorrentSiteDownloaderList.add_downloader(BTMon())
    TorrentSiteDownloaderList.add_downloader(ExtraTorrent())
    TorrentSiteDownloaderList.add_downloader(ExtraTorrentDownload())
    TorrentSiteDownloaderList.add_downloader(YourBittorrent())
    TorrentSiteDownloaderList.add_downloader(H33T())
    TorrentSiteDownloaderList.add_downloader(AliveTorrents())
    TorrentSiteDownloaderList.add_downloader(RARBG())
    TorrentSiteDownloaderList.add_downloader(TorrentReactor())
    TorrentSiteDownloaderList.add_downloader(TorrentZAP())
    TorrentSiteDownloaderList.add_downloader(Fenopy())
    TorrentSiteDownloaderList.add_downloader(FenopyEU())
    TorrentSiteDownloaderList.add_downloader(SeedPeer())
    TorrentSiteDownloaderList.add_downloader(BitTorrentAM())
    TorrentSiteDownloaderList.add_downloader(BTChat())
    TorrentSiteDownloaderList.add_downloader(FullDLS())
    TorrentSiteDownloaderList.add_downloader(MoNova())
    TorrentSiteDownloaderList.add_downloader(SwarmTheHive())
    TorrentSiteDownloaderList.add_downloader(Vertor())
    TorrentSiteDownloaderList.add_downloader(KickAssTorrents())
    TorrentSiteDownloaderList.add_downloader(TorrentPortal())
    TorrentSiteDownloaderList.add_downloader(Torrent1337X())
    TorrentSiteDownloaderList.add_downloader(BitSnoop())
    TorrentSiteDownloaderList.add_downloader(TakeFM())
    TorrentSiteDownloaderList.add_downloader(TorrentsNet())
    #TorrentSiteDownloaderList.add_downloader(TorrentDownloadsNet())
    TorrentSiteDownloaderList.add_downloader(TorrentFunk())
    TorrentSiteDownloaderList.add_downloader(Torrage())
    TorrentSiteDownloaderList.add_downloader(TorCache())
    TorrentSiteDownloaderList.add_downloader(ZoinkIT())
    TorrentSiteDownloaderList.add_downloader(TorrentzMagnet())
    
if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print "Usage : %s url_of_torrent" % (sys.argv[0],)
        sys.exit(0)
    
    Logger.add_logger(ScreenLogger(LOGGING_LEVEL))
    
    LoadOpeners()
    
    TorrentSiteDownloaderList.download_torrent(sys.argv[1])