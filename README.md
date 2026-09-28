# beeminder-commits

GitHubのcommit数（全リポジトリ・private含む）を日ごとに数えて、Beeminderの目標
[chris9609/commits](https://www.beeminder.com/chris9609/commits) へ自動で送る。

Beeminder純正のGitHub連携は「1目標＝1リポジトリ」しか見られないので自作した。

## 流れ
1. GitHubのcommit検索（`author:chris9609`）で直近7日分のcommitを集める
2. author date をJSTに直して日ごとに数える
3. Beeminderに1日1点送る。requestid を `gh-YYYYMMDD` に固定しているので、
   何度送っても点は増えず値だけ更新される（2026/9/28に実測で確認）

## 使い方
```
python3 beeminder_commits.py            # 直近7日分を送る
python3 beeminder_commits.py --dry-run  # 数えるだけ
```
cronで毎時5分に実行。ログは `~/cron/logs/beeminder-commits.log`。

## 鍵
- GitHub：`gh auth token`
- Beeminder：macOSキーチェーン（サービス名 `beeminder-token`、アカウント `chris9609`）
  - 入れ直すとき：`security add-generic-password -U -s beeminder-token -a chris9609 -w`
  - トークンは https://www.beeminder.com/api/v1/auth_token.json （ログイン中に開く）

## 注意
- 数えられるのは各リポジトリの**デフォルトブランチ**のcommitだけ。ブランチ作業はマージされた時点で数えられる
- 目標開始日（2026-09-28）より前の日は送らない
