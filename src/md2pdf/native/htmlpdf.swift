import Cocoa
import WebKit

// htmlpdf <input.html> <output.pdf> [marginPt]
//
// Renders HTML through WebKit (CoreText), so the system PingFang font can be
// embedded, then cuts the page into A4 sheets at element boundaries so that
// paragraphs, list items and table rows are not split across pages.
let args = CommandLine.arguments
guard args.count >= 3 else {
    FileHandle.standardError.write("usage: htmlpdf <input.html> <output.pdf> [marginPt]\n".data(using: .utf8)!)
    exit(2)
}
let inURL = URL(fileURLWithPath: args[1])
let outURL = URL(fileURLWithPath: args[2])
let margin = CGFloat(args.count >= 4 ? (Double(args[3]) ?? 56) : 56)

let A4 = CGSize(width: 595.28, height: 841.89)
let contentW = A4.width - 2 * margin
let pageH = A4.height - 2 * margin

let app = NSApplication.shared
app.setActivationPolicy(.accessory)

func fail(_ message: String) -> Never {
    FileHandle.standardError.write("htmlpdf: \(message)\n".data(using: .utf8)!)
    exit(1)
}

final class Paginator: NSObject, WKNavigationDelegate {
    let web: WKWebView
    let window: NSWindow
    var pages: [(CGFloat, CGFloat)] = []
    var sliceData: [Data] = []
    override init() {
        let cfg = WKWebViewConfiguration()
        web = WKWebView(frame: NSRect(x: 0, y: 0, width: contentW, height: 1000), configuration: cfg)
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: contentW, height: 1000),
                          styleMask: [.borderless], backing: .buffered, defer: false)
        super.init()
        window.contentView = web
        window.orderOut(nil)
        web.navigationDelegate = self
    }
    func go() {
        web.loadFileURL(inURL, allowingReadAccessTo: inURL.deletingLastPathComponent())
        DispatchQueue.main.asyncAfter(deadline: .now() + 60) {
            fail("timed out after 60s waiting for the page to render")
        }
    }

    func webView(_ w: WKWebView, didFinish n: WKNavigation!) {
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.8) { self.measure() }
    }
    func webView(_ w: WKWebView, didFail n: WKNavigation!, withError e: Error) {
        fail("load failed: \(e)")
    }
    func webView(_ w: WKWebView, didFailProvisionalNavigation n: WKNavigation!, withError e: Error) {
        fail("load failed: \(e)")
    }

    func measure() {
        let js = """
        (function(){
          var H=document.body.scrollHeight;
          // Headings are excluded so a heading never ends a page; tr/li are
          // included so tables and lists can break per row with less waste.
          // Anything inside a table cell is skipped so rows stay whole.
          var els=document.body.querySelectorAll('p,pre,blockquote,ul,ol,li,table,tr,hr,figure,header');
          var ys=[0];
          for(var i=0;i<els.length;i++){
            if(els[i].closest('td,th')) continue;
            var r=els[i].getBoundingClientRect();ys.push(Math.round(r.bottom+window.scrollY));
          }
          ys.push(H);
          ys=Array.from(new Set(ys)).filter(function(y){return y>=0;}).sort(function(a,b){return a-b;});
          return JSON.stringify({H:H,ys:ys});
        })()
        """
        web.evaluateJavaScript(js) { res, err in
            guard let s = res as? String, let d = s.data(using: .utf8),
                  let obj = try? JSONSerialization.jsonObject(with: d) as? [String: Any],
                  let H = (obj["H"] as? NSNumber)?.doubleValue,
                  let ysRaw = obj["ys"] as? [NSNumber] else {
                fail("measuring the page failed: \(String(describing: err))")
            }
            let ys = ysRaw.map { CGFloat($0.doubleValue) }
            let total = CGFloat(H)
            var start: CGFloat = 0
            while start < total - 0.5 {
                let target = start + pageH
                if target >= total { self.pages.append((start, total)); break }
                var cut = target
                for y in ys where y > start + 1 && y <= target { cut = y } // ys ascending: last match is the largest
                if cut <= start + 1 { cut = target }                       // one element taller than a page: hard cut
                self.pages.append((start, cut))
                start = cut
            }
            self.renderSlice(0)
        }
    }

    func renderSlice(_ i: Int) {
        if i >= pages.count { assemble(); return }
        let (y0, y1) = pages[i]
        let cfg = WKPDFConfiguration()
        cfg.rect = CGRect(x: 0, y: y0, width: contentW, height: y1 - y0)
        web.createPDF(configuration: cfg) { res in
            switch res {
            case .success(let data): self.sliceData.append(data)
            case .failure(let e): fail("rendering page \(i + 1) failed: \(e)")
            }
            self.renderSlice(i + 1)
        }
    }

    func assemble() {
        if sliceData.isEmpty || sliceData.count != pages.count {
            fail("rendered \(sliceData.count) of \(pages.count) pages")
        }
        let out = NSMutableData()
        guard let consumer = CGDataConsumer(data: out as CFMutableData) else { fail("cannot create PDF consumer") }
        var box = CGRect(origin: .zero, size: A4)
        guard let ctx = CGContext(consumer: consumer, mediaBox: &box, nil) else { fail("cannot create PDF context") }
        for (i, data) in sliceData.enumerated() {
            guard let prov = CGDataProvider(data: data as CFData),
                  let doc = CGPDFDocument(prov), let pg = doc.page(at: 1) else {
                fail("page \(i + 1) is not a readable PDF slice")
            }
            let sliceH = pg.getBoxRect(.mediaBox).height
            ctx.beginPDFPage(nil)
            ctx.saveGState()
            ctx.translateBy(x: margin, y: A4.height - margin - sliceH) // slice top aligned to the top margin
            ctx.drawPDFPage(pg)
            ctx.restoreGState()
            ctx.endPDFPage()
        }
        ctx.closePDF()
        do { try out.write(to: outURL); exit(0) }
        catch { fail("cannot write \(outURL.path): \(error)") }
    }
}

let p = Paginator()
p.go()
app.run()
