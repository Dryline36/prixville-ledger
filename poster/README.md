# Ledger poster

Posts one draft from your own X account. It will not send unless you pass `--confirm`.

This is not Grok Bot. Grok Bot cannot post. This app can, because it uses tokens you create.

## Once

1. developer.x.com → a project and an app with Read and write.
2. User authentication: OAuth 1.0a. Callback can be `http://localhost`.
3. Keys and tokens → generate Access Token and Secret for the account that should post.
4. `cp .env.example .env` and fill the four values. `.env` is gitignored.

## Send

```
pip install requests
python post.py
python post.py --confirm --image ../x/ledger-board.png --image ../x/ledger-dossier.png --image ../x/ledger-crowd.png
```

The first command prints the draft and stops. The second posts `draft.txt` with up to 4 images.

X checks the posting account, not the API plan, for image size. Photos must be 5 MB or under.
