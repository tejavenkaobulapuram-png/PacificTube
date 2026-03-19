# 🎬 Pacific Tube

YouTube風の社内動画ライブラリアプリケーション  
Azure Blob Storageに保存された動画を表示します

## 🚀 特徴

- ✅ **YouTube風のUI** - モダンで使いやすいインターフェース
- ✅ **動画サムネイル自動生成** - 各動画のプレビュー画像を表示
- ✅ **Azure Blob Storage連携** - SASトークンによる安全なアクセス
- ✅ **フォルダナビゲーション** - 左サイドバーでフォルダ階層を表示
- ✅ **視聴回数トラッキング** - YouTube風の視聴回数表示
- ✅ **検索機能** - 動画名で素早く検索
- ✅ **レスポンシブデザイン** - PC・タブレット・スマホ対応
- ✅ **シンプルなデプロイ** - Pythonだけで動作

## 📋 必要要件

- Python 3.8以上
- Azure Blob Storage アカウント
- インターネット接続

## ⚙️ セットアップ

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 2. 設定ファイルの確認

`config.py` を開いて、以下の設定を確認してください：

```python
STORAGE_ACCOUNT_NAME = "pacifictubestorage"
CONTAINER_NAME = "videos"
SAS_TOKEN = "your_sas_token_here"
```

### 3. アプリケーションの起動

```bash
python app.py
```

ブラウザで http://localhost:5000 を開いてください

## 📁 プロジェクト構造

```
PacificTube/
├── app.py                 # Flask アプリケーション (メイン)
├── config.py              # Azure Blob Storage設定
├── view_tracker.py        # 視聴回数トラッキングシステム
├── views.json             # 視聴データ保存ファイル (自動生成)
├── requirements.txt       # Python依存関係
├── templates/
│   └── index.html        # HTMLテンプレート
└── static/
    ├── style.css         # CSSスタイル
    └── script.js         # JavaScriptロジック
```

## 📊 視聴回数機能

動画が再生されると自動的に視聴回数がカウントされます：

- **表示形式**: YouTube風 (100回視聴, 1.2K回視聴, 1.5M回視聴)
- **データ保存**: `views.json` ファイルに自動保存
- **リアルタイム更新**: 動画再生時に即座にカウント

視聴データはローカルファイルに保存されるため、サーバーを再起動してもデータは保持されます。

## 🖼️ サムネイル自動生成

各動画のサムネイル（プレビュー画像）が自動的に生成されます：

- **自動抽出**: 動画の最初の数秒からフレームを抽出
- **ブラウザ処理**: JavaScript/Canvas APIで生成（サーバー負荷なし）
- **YouTube風デザイン**: 16:9アスペクト比で表示
- **キャッシュ**: ブラウザにキャッシュされるため高速表示

サムネイルは動画ファイルから自動的に生成されるため、追加のファイルアップロードは不要です。

## 🎥 動画のアップロード

### Azure Portalでのアップロード:

1. https://portal.azure.com にアクセス
2. Storage accounts → **pacifictubestorage**
3. Containers → **videos**
4. **Upload** ボタンをクリック
5. 動画ファイルを選択してアップロード

### Azure CLIでのアップロード:

```bash
az storage blob upload --account-name pacifictubestorage --container-name videos --name "video.mp4" --file "path/to/video.mp4" --auth-mode login
```

## 🔐 セキュリティ

このアプリケーションはSASトークンを使用して、プライベートなBlob Storageにアクセスします。

**重要:** SASトークンの有効期限は **2027-03-19** です。  
期限が切れたら、新しいトークンを生成してください：

```bash
az storage container generate-sas --account-name pacifictubestorage --name videos --permissions rl --expiry 2028-03-19T23:59:59Z --https-only --output tsv
```

## 🌐 デプロイ

### 社内サーバーへのデプロイ:

1. プロジェクトフォルダを社内サーバーにコピー
2. 依存関係をインストール: `pip install -r requirements.txt`
3. アプリケーションを起動: `python app.py`
4. ファイアウォールでポート5000を開放

### 本番環境での起動 (Gunicorn):

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## 🛠️ トラブルシューティング

### 動画が表示されない場合:

1. `config.py` の設定を確認
2. SASトークンの有効期限を確認
3. Azure Blob Storageに動画がアップロードされているか確認

### エラーメッセージが表示される場合:

- ブラウザのコンソール (F12) でエラーを確認
- `python app.py` を実行してターミナルのログを確認

## 📞 サポート

問題がある場合は、IT部門にお問い合わせください。

---

**作成日:** 2026-03-19  
**バージョン:** 1.0.0
