# SemiCSP Radar

半導體與 CSP 產業鏈情報儀表板 MVP。

## 目前包含

- 國際情勢與台灣本土兩條主線
- CSP、晶片設計、晶圓代工、HBM、先進封裝、設備、AI 伺服器、政策分類
- RSS 抓取、SQLite 去重、JSON 輸出
- 靜態 HTML 儀表板：半導體動態與股市動態分頁
- 左側歷史時間線
- 右下角回到頂部按鈕
- 每日資料歸檔：`site_data/daily/YYYY-MM-DD/news.json`
- 網頁可讀歷史索引：`docs/data/history.json`
- 股市觀察欄位：台灣加權指數、半導體供應鏈股票、Yahoo 股市新聞

## 快速啟動

產生示範資料：

```powershell
python .\radar.py --sample
```

抓取線上 RSS：

```powershell
python .\radar.py
```

啟動本機儀表板：

```powershell
python .\server.py
```

瀏覽：

```text
http://localhost:8787
```

公開部署版右上角按鈕是「重新載入資料」，用來讀取最新已產生的 JSON。真正的資料更新由 GitHub Actions 約每 30 分鐘自動執行。

## 資料夾結構

```text
site_data/
  history.json
  daily/
    YYYY-MM-DD/
      news.json

docs/
  data/
    news.json
    history.json
    daily/
      YYYY-MM-DD/
        news.json
```

`site_data` 是網站的專屬長期資料夾，依日期保存每日快照。`docs/data` 是前端網站直接讀取的資料副本。

## 下一步建議

- 接 OpenAI API，把規則式摘要替換成投資研究風格摘要
- 加入每日排程，例如 Windows Task Scheduler 或 GitHub Actions
- 加入 Email、LINE、Telegram 或 Slack 推送
- 擴充付費/授權資料源，例如 Bloomberg、FactSet、Refinitiv、鉅亨、MoneyDJ 或 DIGITIMES 會員內容

## 股市資料

股市觀察欄位目前追蹤：

- 大盤：台灣加權指數
- 半導體供應鏈：台積電、鴻海、廣達、緯穎、緯創、聯發科、日月光投控、欣興、南電、創意、健策、台達電
- Yahoo 股市 RSS：台股動態、研究報導、國際財經

報價用於快速觀察市場情緒，不構成投資建議。

## GitHub Pages 公開部署

建議部署方式：

1. 在 GitHub 建立一個 public repository，例如 `semicsp-radar`
2. 把本資料夾內容推上 GitHub
3. 到 GitHub repo 的 `Settings > Pages`
4. Source 選 `Deploy from a branch`
5. Branch 選 `main`，Folder 選 `/docs`
6. 儲存後等待 GitHub Pages 產生網址

公開網址通常會像：

```text
https://你的GitHub帳號.github.io/semicsp-radar/
```

定期更新：

- `.github/workflows/update-data.yml` 會約每 30 分鐘自動執行 `python radar.py`
- 也可以在 GitHub Actions 頁面手動按 `Run workflow`
- 更新後網站會讀取新的 `docs/data/news.json`

## 本機網址說明

目前網址是本機網址：

```text
http://127.0.0.1:8787
```

這不是公開永久網址，只在你的電腦啟動 `server.py` 時有效。正式分享請使用 GitHub Pages 產生的公開網址。你也可以更改：

- Port：修改 `server.py` 裡的 `port = 8787`
- 本機名稱：可用 `localhost:8787`
- 公開永久網址：需要部署到 Vercel、Render、Railway、公司內網主機，或綁定自己的網域名稱
