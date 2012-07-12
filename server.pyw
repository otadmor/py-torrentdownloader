import torrent_downloader
import SimpleHTTPServer
import SocketServer
import threading

PORT = 12345
LOGGING_LEVEL = 0

class TorrentRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
	def __init__(self, *args, **kargs):
		SimpleHTTPServer.SimpleHTTPRequestHandler.__init__(self, *args, **kargs)
		
	def do_GET(self):
		if self.request.getpeername()[0] != "127.0.0.1" and not self.request.getpeername()[0].startswith("10.0.0."):
			self.wfile.write("Noob")
		else:
			threading.Thread(target = torrent_downloader.TorrentSiteDownloaderList.download_torrent, args = (self.path[1:],)).start()
		
		
if __name__ == "__main__":
	import os
	os.chdir(os.path.dirname(__file__))
	torrent_downloader.Logger.add_logger(torrent_downloader.FileLogger("log.txt", LOGGING_LEVEL))
	torrent_downloader.Logger.add_logger(torrent_downloader.ScreenLogger(LOGGING_LEVEL))
	torrent_downloader.LoadOpeners()	
	
	torrent_server = SocketServer.ThreadingTCPServer(('0.0.0.0', PORT),TorrentRequestHandler)

	torrent_server.serve_forever()