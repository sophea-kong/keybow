# Kibo-RPC 7th Programming Manual

![Kibo-RPC 7th](./images/Cover.png)

| 項目 | 内容 |
|---|---|
| 対象 | Kibo-RPC 7th 参加者 |
| 版数 | 1.0 |
| 最終更新日 | 2026-10-05 |
| 発行元 | 国立研究開発法人宇宙航空研究開発機構 (JAXA) |
| 問合わせ先 | z-krpc7@ml.jaxa.jp |

## 改訂履歴

| 改訂日 | バージョン | 段落 | 改訂場所 |
|---|---|---|---|
| 2026-10-05 | 1.0 | - | - |

# 本書について

本書は、Int-Ball2向けアプリケーションの開発、ビルド、シミュレーションに必要な情報を提供するプログラミングマニュアルです。

本書では、初めてKibo-RPCに参加する読者が、開発環境の準備からプログラムの実行、結果確認までを順に進められる構成としています。

## 対象読者

- Int-Ball2向けアプリケーションを初めて開発する方
- シミュレータを利用してプログラムを検証する方
- 開発環境やAPI仕様を確認したい方

## 本書でできるようになること

本書を読み進めることで、以下を実施できるようになります。

- 開発に必要な環境を準備する
- 提供されるサンプルコードからアプリケーションを作成する
- Webシミュレータおよびローカルシミュレータでプログラムを実行する
- 実行状況、ログ、シミュレーション結果を確認する
- Kibo-RPC APIの役割と利用方法を確認する

# 凡例

| 表記 | 意味 |
|---|---|
| `command` | コマンド、API名、メッセージ型、ファイル名、ディレクトリ名、設定値など、コードやターミナルで入力・参照する値 |
| `[画面項目]` | ボタン、メニュー、タブなどの画面要素 |
| `<PLACEHOLDER>` | 利用者または環境に応じて置き換える値。コードブロック内の構文要素は除きます |

> [!NOTE]
> 手順や仕様に関する補足情報を示します。

> [!CHECK]
> 必須条件、事前確認、安全性、実機運用、提出物に関係する確認事項を示します。

> [!WARNING]
> 誤操作や設定ミスにより、プログラム停止、データ消失、機器への影響が生じる可能性がある事項を示します。

> [!TIP]
> 作業を進めやすくするための補足情報や推奨事項を示します。

# 目次

1. [はじめに](#1-はじめに)
2. [セットアップ](#2-セットアップ)
3. [アプリケーション作成](#3-アプリケーション作成)
4. [シミュレータでのプログラム実行](#4-シミュレータでのプログラム実行)
5. [プログラムのヒント](#5-プログラムのヒント)
6. [Game APIの詳細](#6-game-apiの詳細)

## 本書の構成

| 章 | 内容 |
|---|---|
| 第1章 | 本書の目的、対象読者、開発の全体像 |
| 第2章 | 動作環境、開発ツールのセットアップ |
| 第3章 | プロジェクト作成、実装、設定、ビルド |
| 第4章 | Webシミュレータおよびローカルシミュレータでの実行 |
| 第5章 | 安定したプログラムを作るための設計上のヒント |
| 第6章 | Game APIの一覧と詳細 |

# 1. はじめに

## 1.1 Int-Ball2について

> Int-Ball2は、ISSで活動する宇宙飛行士を支援する船内ドローンです。
> 
> 宇宙飛行士は地上の管制官と協力して様々な実験やISSのメンテナンス作業を実施しています。Int-Ball2は地上の管制官の操作によりISS内を飛び回り、写真や動画の撮影を宇宙飛行士の代わりに行います。  
> 現在、「きぼう」日本実験棟内での写真・動画撮影は、宇宙飛行士がカメラを自身で準備して実施していますが、地上からの遠隔操作でInt-Ball2が行うことで、その準備や撮影に要する宇宙飛行士の作業時間を軽減できます。

引用: [JAXA有人宇宙技術部門HP](https://humans-in-space.jaxa.jp/news/detail/003155.html)

## 1.2 プログラミングの全体像

Int-Ball2向けプログラムの開発は、原則として以下の流れで行います。

1. 開発環境を準備する
2. Kibo-RPCが提供するワークディレクトリを取得する
3. アプリケーションを作成する
4. シミュレータで動作を確認する
5. ログと実行結果を確認する
6. 必要に応じてプログラムを修正する

## 1.3 開発を始める前の注意事項

- 本書とあわせて、大会の最新ルールブックおよびガイドブック、シミュレータの操作手順、シミュレータのバージョン情報、プログラムの作成・提出に関する制約事項を確認してください。
- シミュレータとInt-Ball2実機では、利用できる機能や動作特性が異なる場合があります。
- 実機で使用するプログラムだけでなく、シミュレータで使用するプログラムであっても安全性と安定性を優先して設計してください。
- バージョンが指定されているツールやライブラリは、自己判断で更新しないでください。
- 重要な設定変更や実機操作の前には、バックアップと事前確認を行ってください。

# 2. セットアップ

## 2.1 セットアップの流れ

> [!NOTE]
> **「Linux」と「Ubuntu」の違いについて**  
> 本書では「Linux環境」という表記がたびたび登場しますが、これは「Ubuntu」という特定のLinuxディストリビューション（Linuxの種類の1つ）を導入した環境を指します。Linuxには他にも多くのディストリビューションが存在しますが、本書はUbuntuを前提として手順を説明します。
>
> - **Linux**：OSの一種を指す総称です。Ubuntuの他にも多くの種類（ディストリビューション）があります。
> - **Ubuntu**：Linuxディストリビューションの1つで、本書が動作対象とする環境です。
> - **WSL2**：Windows上でLinux（Ubuntu）環境を動かすための仕組み（Windows Subsystem for Linux 2）です。Windowsを利用する場合は、WSL2を使ってWindows上にUbuntu環境を用意します。手順は[2.4.1 Windows 11 での WSL2 と Ubuntu のインストール](#241-windows-11-での-wsl2-と-ubuntu-のインストール)を参照してください。
>
> 以降、本書で単に「Linux環境」と記載している箇所は、「Ubuntu環境（Windowsを利用する場合はWSL2上のUbuntu）」を意味します。

利用するシミュレータに応じて、必要なセットアップが異なります。

- **Webシミュレータのみを利用する場合**：Linux環境（Ubuntu）を用意し、[2.5 開発用リソースの取得](#25-開発用リソースの取得)を行ってから、[3. アプリケーション作成](#3-アプリケーション作成)の手順に進みます。Dockerのインストールは不要です。
- **ローカルシミュレータも利用する場合**：動作環境を確認し、[2.4 基本ツールのインストール](#24-基本ツールのインストール)でDockerをインストールしてから、開発用リソースを取得し、[3. アプリケーション作成](#3-アプリケーション作成)および[4.4 ローカルシミュレータ](#44-ローカルシミュレータ)の手順に進みます。

> [!NOTE]
> どちらの場合も、開発用リソースの展開や提出用アーカイブの作成にLinux環境（Ubuntu）が必要です。Windowsを利用する場合は、WSL2上のUbuntuを使用してください。

## 2.2 動作環境

> [!NOTE]
> 必要となる条件は、ローカルシミュレータを実行するかどうかで異なります。
>
> - **Webシミュレータのみを利用する場合**：[2.2.1 ローカルシミュレータ実行時の動作環境](#221-ローカルシミュレータ実行時の動作環境)のハードウェア要件の確認とDockerのインストール（[2.4.2](#242-docker-のインストール)）は不要です。ただし、開発用リソースの展開と提出用アーカイブの作成にLinux環境（Ubuntu）を使用するため、Windowsを利用する場合はWSL2とUbuntuの導入（[2.4.1](#241-windows-11-での-wsl2-と-ubuntu-のインストール)）が必要です。
> - **ローカルシミュレータも利用する場合**：[2.2.1 ローカルシミュレータ実行時の動作環境](#221-ローカルシミュレータ実行時の動作環境)のハードウェア要件を満たしたうえで、Dockerのインストール（[2.4.2](#242-docker-のインストール)）が必要です。Windowsを利用する場合は、あわせてWSL2とUbuntuの導入（[2.4.1](#241-windows-11-での-wsl2-と-ubuntu-のインストール)）も必要です。

### 2.2.1 ローカルシミュレータ実行時の動作環境

| 項目 | 最低条件 | 推奨条件 | 備考 |
|---|---|---|---|
| OS | Ubuntu 20.04以上 | Ubuntu 24.04 | Windows 11 を利用する場合は WSL2 上で Ubuntu を利用すること |
| CPU | 4コア以上 | 6コア以上 | 複数プロセスの同時実行に影響 |
| メモリ | 8GB 以上 | 16GB 以上 | WSL2 利用時はメモリ不足に注意 |
| ストレージ | 20GB 以上の空き容量 | 40GB 以上推奨 | SSD を推奨 |

### 2.2.2 利用環境について

- ローカル環境のメモリが不足している場合は、WSL2のメモリ設定を確認し、WindowsおよびWSL2上で不要なアプリケーションやプロセスを停止してください。
- シミュレータが正常に動作しない場合は、不要なアプリケーションやバックグラウンドプロセスを終了し、メモリとCPUを確保してから再度実行してください。
- ローカル環境を用意できない場合は、Webシミュレータ環境を利用してください。  
利用方法については[4.2 Webシミュレータ](#42-webシミュレータ)を参照してください。

> [!CHECK]
> Windows 11 でローカルシミュレータを利用する場合は、WSL2 をインストールして Ubuntu 環境を作成したうえで実行します。
> Windows 11 のみでの実行は対象外です。

### 2.2.3 WSL2 利用時の注意

> [!WARNING]
> WSL2 での実行は可能ですが、メモリ不足により動作が不安定になる場合があります。
> 不要なバックグラウンドアプリを終了し、十分なメモリを確保してから実行してください。
> Docker や WSL2 のセットアップに関する詳細は、[WSL公式ドキュメント](https://learn.microsoft.com/windows/wsl/install)や各環境のセットアップガイドを参照してください。

## 2.3 必要なソフトウェア

| ソフトウェア | 用途 | 必須・推奨 |
|---|---|---|
| VSCode | ソースコードの編集 | 推奨 |
| Git | ソースコード管理 | 推奨 |
| Docker | ローカルシミュレータ実行 | 必須 |

シミュレータ環境では、以下のバージョンを使用します。

| 項目 | バージョン |
|---|---|
| GCC | 7.5.0 |
| C++ | C++14 |
| Python | 3.6.9 |
| ROS | ROS 1 Melodic |

## 2.4 基本ツールのインストール

> [!NOTE]
> 本節では、ローカルシミュレータを実行するための WSL2、Ubuntu、Docker の導入手順を説明します。
> Ubuntu を利用している方、または WSL2 と Ubuntu の導入が完了している方は、[2.4.2 Docker のインストール](#242-docker-のインストール)から進めてください。

### 2.4.1 Windows 11 での WSL2 と Ubuntu のインストール

Windows 11 を利用する場合は、開発用リソースの展開と提出用アーカイブの作成のために、WSL2 上に Ubuntu 環境を用意します。ローカルシミュレータもこの環境で実行されます。  
Windows のコマンドプロンプトまたは PowerShell を管理者として起動し、以下を実行してください。

```powershell
wsl --install -d Ubuntu-24.04
```

インストール後、Ubuntu が起動したら、画面の案内に従ってユーザ名とパスワードを設定してください。

> [!NOTE]
> Windows の再起動を求められた場合は、以下を実行して Windows を再起動してから、Ubuntu を起動してユーザ名とパスワードを設定してください。

```powershell
shutdown /r /t 0
```

設定が完了したら、Windows の PowerShell で以下を実行し、WSL2 が利用されていることを確認します。

```powershell
wsl --list --verbose
```

Ubuntu の VERSION が `2` になっていることを確認してください。VERSION が `1` の場合は、管理者権限の PowerShell で以下を実行して WSL2 に変更します。`<DISTRO_NAME>` には、`wsl --list --verbose` の NAME 列に表示されたディストリビューション名（例: `Ubuntu-24.04`）をそのまま指定してください。

```powershell
wsl --set-version <DISTRO_NAME> 2
```

> [!CHECK]
> Windows 11 のローカルシミュレータ実行では、WSL2 と Ubuntu の利用が必須です。Windows のコマンドプロンプトや PowerShell から直接シミュレータを実行するのではなく、以降の手順は Ubuntu のターミナルで実行してください。

### 2.4.2 Docker のインストール

Ubuntu のターミナルで以下を実行し、Docker の公式リポジトリを登録して Docker Engine をインストールします。

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo \"$VERSION_CODENAME\") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Docker を一般ユーザから実行できるように設定し、設定を反映するため Ubuntu を再起動します。

```bash
sudo usermod -aG docker $USER
```

WSL の Ubuntu ターミナルをいったん終了して再起動した後、以下で Docker が利用できることを確認してください。

```bash
docker run hello-world
```

### 2.4.3 推奨ツール（Git と VSCode）のインストール

Git とエディタは、プログラムの取得や編集に使用します。どちらも必須ではありませんが、本書では無料で利用でき、操作しやすい Git と VSCode (Visual Studio Code) を推奨します。

#### Git のインストール

Git は WSL2 上の Ubuntu で使用するため、Ubuntu 環境にインストールしてください。Ubuntu のターミナルで以下を実行します。

```bash
sudo apt-get update
sudo apt-get install -y git
git --version
```

`git --version` を実行して、Git のバージョンが表示されることを確認してください。

#### VSCode のインストール

エディタは任意のものを利用できます。本書では、無料で利用でき、拡張機能が豊富で、WSL2 との連携が容易な Visual Studio Code（VSCode）を推奨します。以下の公式サイトから Windows 版のインストーラーを取得してインストールしてください。

- [Visual Studio Code](https://code.visualstudio.com/Download)

> [!CHECK]
> Windows 11 で VSCode を利用する場合は、Windows 側にインストールした VSCode から WSL2 の Ubuntu 環境に接続して使用してください。  
> Windows 側のファイルを直接編集するのではなく、Ubuntu 環境内のワークスペースを開いて編集します。

VSCode の拡張機能ビューから、以下の拡張機能をインストールしてください。

- [WSL 拡張機能](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-wsl)

拡張機能をインストールすると、VSCode から WSL2 の Ubuntu 環境に接続できるようになります。
![Connect_WSL_on_VSCode_1](./images/Connect_WSL_on_VSCode_1.png)

1. 左下の「><」アイコンをクリックします。
2. [Connect to WSL] を選択します。

![Connect_WSL_on_VSCode_2](./images/Connect_WSL_on_VSCode_2.png)

- 左下に「WSL: Ubuntu」が表示されていれば、WSL2 の Ubuntu 環境に接続されています。

## 2.5 開発用リソースの取得

開発に必要なリソースは、GZIP 形式のアーカイブファイルで提供します。  
以下のダウンロードページから、対象のアーカイブファイルを取得してください。

- [Download | Kibo Robot Programming Challenge](https://jaxa.krpc.jp/download)

> [!NOTE]
> 配布形式および配布場所は、今後変更される可能性があります。

### 2.5.1 開発用リソースの取得

1. [Download | Kibo Robot Programming Challenge](https://jaxa.krpc.jp/download) にアクセスします。
2. 開発用リソースの tar ファイル (KRPC7 Simulator Resources) をダウンロードします。
3. ダウンロードしたファイルの破損がないことを確認します。

![Download_page](./images/Download_krpc_simulator_resources.png)

### 2.5.2 開発用リソースの展開

Ubuntu または WSL2 の Ubuntu ターミナルで、ダウンロードした tar ファイルを任意の作業ディレクトリに展開します。

```bash
mkdir -p ~/krpc
tar -xvf krpc7th-simulator.tar.gz -C ~/krpc
```

tar ファイルを展開すると、以下のディレクトリ構成が得られます。  
本書は、以降すべてこの2.5.2で展開した `krpc7th-simulator/` ディレクトリを前提に説明します。

```text
krpc7th-simulator/
├── build.sh                       # シミュレータをビルドするスクリプト
├── simulation.sh                  # シミュレータを1回起動して実行するスクリプト
├── replay.sh                      # 実行結果（rosbag）をリプレイするスクリプト
├── docker-compose.yaml            # シミュレータ本体とユーザプログラム用コンテナの定義
├── docker-compose.replay.yaml     # リプレイ用コンテナの定義
├── README.md
├── docs/                          # マニュアルと画面キャプチャ
│   ├── ProgrammingManual.md       # 英語版マニュアル
│   ├── ProgrammingManual_ja.md    # 日本語版マニュアル
│   └── images/                    # マニュアル内で使用する画像
├── docker/                        # シミュレータイメージのビルド定義（編集不要）
│   ├── Dockerfile.krpc-base       # シミュレータ本体（ROS/Gazebo等）のビルド定義
│   ├── Dockerfile.krpc-replay     # リプレイ用イメージのビルド定義
│   ├── ros_overlay/src/           # イメージに組み込まれるROSパッケージ
│   └── ros_python3_overlay/src/   # イメージに組み込まれるPython3用ROSパッケージ
├── rootfs/                        # シミュレータ実行スクリプト（編集不要）
├── rviz/                          # シミュレータのRViz表示設定（編集不要）
├── users/                         # ★参加者が編集する作業ディレクトリ
│   ├── README.md                  # ソースコード提出手順
│   ├── packing.sh                 # 提出用アーカイブ（tar.gz）を作成するスクリプト
│   ├── bootstrap/                 # ユーザプログラムのビルド・起動処理（編集不要）
│   │   ├── build-user.sh          # ユーザのcatkin_wsをビルドする処理
│   │   ├── boot-ib2.sh            # ビルドしたユーザプログラムを起動する処理
│   │   └── tail_log.sh            # ユーザプログラムのログをリアルタイム表示する処理
│   └── catkin_ws/
│       └── src/
│           ├── krpc_user/         # ★参加者が実装するメインパッケージ
│           ├── krpc_api_server/   # 提供されるAPIサーバパッケージ（変更禁止）
│           ├── krpc_ib2_msgs/     # 提供されるメッセージ／アクション定義（変更禁止）
│           └── CMakeLists.txt
└── share/                         # 実行結果の出力先（実行するたびに生成される）
    └── logs/
        ├── latest/                # 直近の実行結果への参照（textures/iss.urdfなど）
        └── <timestamp>/           # 実行ごとの結果一式
            ├── cheat_sheet.json          # その回のチェックポイント配置
            ├── simulation.bag            # 実行全体のrosbag記録（replay.shで再生）
            ├── judge_module_logs/        # 採点ログ
            └── user_programs_logs/       # ユーザプログラム自身の標準出力・ROSログ
```

### ディレクトリの役割まとめ

| ディレクトリ／ファイル | 編集可否 | 役割 |
|---|---|---|
| `users/catkin_ws/src/krpc_user/` | **編集する（メイン）** | ミッションロジックを実装する参加者パッケージ |
| `users/catkin_ws/src/krpc_api_server/`, `krpc_ib2_msgs/` | 編集しない（参照のみ） | 提供されるAPIサーバおよびメッセージ定義 |
| `users/packing.sh`, `users/bootstrap/` | 編集しない（そのまま利用） | 提出用パッケージ作成、ビルド・起動処理 |
| `docker/`, `rootfs/`, `rviz/` | 編集しない | シミュレータイメージのビルド・実行用インフラ |
| `share/` | 編集しない（結果を確認） | 実行のたびに生成されるログ・採点結果・rosbag |
| `build.sh`, `simulation.sh`, `replay.sh`, `docker-compose*.yaml` | 編集しない（そのまま実行） | シミュレータのビルド・実行・リプレイの入り口 |

> [!WARNING]
> 参加者が編集するのは、原則として `users/catkin_ws/src/krpc_user/` のみです。`krpc_api_server`、`krpc_ib2_msgs` およびその他のインフラ用ディレクトリは参照のみとし、変更しないでください。

# 3. アプリケーション作成

## 3.1 VSCode でサンプルコードを開く

1. VSCode を起動します。
2. `[File]` をクリックします。
3. `[Open Folder]` をクリックします。
4. `~/krpc/krpc7th-simulator/users/` を指定します。
5. サンプルコードが VSCode で開かれることを確認します。

![Open Folder in VSCode](./images/Open_Folder_in_VSCode.png)

> [!NOTE]
> 開発用リソースのダウンロードと tar ファイルの展開は、[2.5 開発用リソースの取得](#25-開発用リソースの取得) で説明しています。

## 3.2 サンプルコードの修正

1. `~/krpc/krpc7th-simulator/users/catkin_ws/src/krpc_user/` にサンプルコードが配置されていることを確認します。
2. サンプルコードを必要に応じて修正します。
3. 修正が完了したら、`users/packing.sh` を実行して提出用パッケージを作成します。

> [!CHECK]
> `users/packing.sh`はシェルスクリプトです。Linux環境（Ubuntu）で実行してください。Windowsを利用する場合は、WSL2上のUbuntuターミナルを使用します。Webシミュレータのみを利用する場合も、このスクリプトで提出用アーカイブを作成するため、Linux環境（Ubuntu）が必要です。

```bash
cd ~/krpc/krpc7th-simulator/users
./packing.sh YourSourceCode
```
4. 作成された提出用パッケージをWebシミュレータで実行します。

> [!NOTE]
> ローカルシミュレータでの実行は [4.4 ローカルシミュレータ](#44-ローカルシミュレータ) を参照してください。

# 4. シミュレータでのプログラム実行

## 4.1 シミュレータの種類

| 項目 | Webシミュレータ | ローカルシミュレータ |
|---|---|---|
| 主な用途 | 提出前確認、共通環境での評価 | 開発中の動作確認、デバッグ |
| 実行場所 | Kibo-RPC運営が管理するサーバー | 開発者PC |
| CPUアーキテクチャ | ARM64（aarch64）環境を採用し、実機に近い条件で実行 | 一般的な開発者PCで利用される x86_64 環境が中心 |
| 利用アカウント | [HP \| Kibo Robot Programming Challenge](https://jaxa.krpc.jp/) から、自分の国または地域の POC に登録申請し、発行されたアカウントを利用 | 原則不要 |
| ログ | Web ダッシュボードから取得可能 | ローカル環境に保存 |

## 4.2 Webシミュレータ

### 4.2.1 マイページへのログイン

1. [Login | Kibo Robot Programming Challenge](https://jaxa.krpc.jp/user-auth/) にアクセスします。
2. 各自の国または地域の POC から発行されたアカウントでログインします。
3. Kibo-RPC のマイページが表示されることを確認します。

![Login Page](./images/Login_Page.png)

### 4.2.2 シミュレーションの実行

1. Kibo-RPC のマイページを開いている画面から、`[SIMULATION]` をクリックします。
2. 提出フォームに実行する `YourSourceCode.tar.gz` をドラッグ＆ドロップするか、ファイルを選択して提出します。

提出フォームには、以下の画面項目があります。

| 項目 | 入力方法 | 説明 |
|---|---|---|
| Simulator Level | プルダウンリスト | シミュレーションの難易度を選択します。 |
| Simulator Version | プルダウンリスト | 使用するシミュレータのバージョンを選択します。 |
| Memo | テキストフォーム | シミュレーションに関するメモを入力します。 |

3. `[START SIMULATION]` をクリックします。
4. 確認ダイアログが表示されたら、`[OK]` をクリックします。
5. シミュレーションが開始されることを確認します。

![Simulation Execution](./images/Simulation_Execution_1.png)
![Simulation Execution](./images/Simulation_Execution_2.png)
![Simulation Execution](./images/Simulation_Execution_3.png)

### 4.2.3 シミュレーション結果の確認

1. シミュレーションが完了したことを確認します。 Status が "Finished" になっているシミュレーションが完了済みです。
2. 結果を確認するためには`[VIEW RESULT]` をクリックします。

![Simulation Result](./images/Simulation_Result.png)

> [!NOTE]
> 結果画面では、シミュレーションのステータスやスコア、各種ログへのアクセスが可能です。
> 各画面項目については、後述の[4.3 シミュレーション結果の確認](#43-シミュレーション結果の確認)を参照してください。

### 4.2.4 シミュレーションのリプレイ

1. Finished 状態のシミュレーションを開きます。
2. `[SIMULATOR VIEWER]` をクリックします。
3. 表示されたダイアログの `[Password]` をコピーします。
4. ダイアログの `[VIEW]` をクリックします。
5. 別タブでリプレイ画面が表示されます。
6. `[Speed]` スライダーを調整して再生速度を設定します。
7. `[Play]` をクリックします。
8. シミュレーションがリプレイされることを確認します。

![Simulation Replay](./images/Simulation_Replay_1.png)
![Simulation Replay](./images/Simulation_Replay_2.png)
![Simulation Replay](./images/Simulation_Replay_3.png)
![Simulation Replay](./images/Simulation_Replay_4.png)

## 4.3 シミュレーション結果の確認

### 4.3.1 結果画面

![Simulation Dashboard](./images/Simulation_Dashboard.png)

| 項目 | 説明 |
|---|---|
| Status | シミュレーションの実行状態 |
| Executed | シミュレーションを実行した日時 |
| Team | 実行したチーム名 |
| Country/Region | 国または地域 |
| Source Code | 実行したソースコードのファイル名 |
| Course | 実行したコース |
| Simulator Level | シミュレーションの難易度（Easy、Normal、Hard、Very Hardなど） |
| Simulator Version | 実行に使用したシミュレータのバージョン |
| Memo | シミュレーションに関するメモ |
| Final Score | 最終スコア |
| Mission Time | ミッションの実行時間 |
| Time Bonus | シミュレーション時間の倍率 |
| CheckPoints Passed  | 成功したチェックポイント数 |
| Goal Reached | ゴール到達の有無 |

#### Score Breakdown

結果画面のスコアは、単一の数値だけでなく、以下の要素が積み重なって決まります。各項目を確認することで、どの動作が得点に寄与したかを把握できます。

- `CheckPoint Score Total`  
  チェックポイントの合計スコアです。  
  詳細はCheckPoint Detailで確認できます。

- `Level Summary`  
  各レベルの達成数を示します。

- `Goal Score`  
  ゴール判定が成立した場合、ゴールスコアが加算されます。

#### CheckPoint Detail

各チェックポイントの通過結果をまとめたリストです。  
難易度によってチェックポイントの数や配置が変わります。『N/A』と表示されたチェックポイントは、評価対象外です。

- `Check Point`  
  チェックポイントの識別番号です。どのマーカーまたは地点を通過したかを示します。

- `Result`  
  そのチェックポイントを正しく通過できたかどうかを表します。`PASSED` の場合は成功、`FAIL` は未通過または失敗を意味します。

- `Level`  
  チェックポイント通過時の総合評価レベルです。位置、カメラ視線のセンタリング、視線軸回りの姿勢についてそれぞれ判定したレベルのうち、最も低いレベルが採用されます。いずれかの条件がマージン外の場合は通過失敗となり、`-`で表示されます。`Lv3`は3条件を満たした場合の高評価例です。各条件の詳細は[6.3.1 ミッションイベントAPI](#631-ミッションイベントapi)を参照してください。

- `Score`  
  そのチェックポイントで獲得した得点です。評価レベルに応じてスコアが決まり、最終スコアの計算に使用されます。

> [!TIP]
> スコアを改善したい場合は、まず `CheckPoints Passed` と `Goal Reached` を満たし、そのうえで `Time Bonus` を最大化することが効果的です。チェックポイントでは、位置マージンに加えて、カメラ視線をマーカー中心に向けることと、視線軸回りの姿勢マージンを満たすことが得点に影響します。

### 4.3.2 ログファイル/結果ファイルのダウンロード

`[DOWNLOAD LOG FILES]` からは、次の2種類のファイルを取得できます。両者は別のファイルです。

| 種類 | 内容 |
|---|---|
| 結果ファイル（JSON） | 採点結果です。違反の有無、ミッションの実行情報、チェックポイントの詳細、ゴールの結果、実行中に発生したイベントが含まれます |
| ユーザプログラムのログ | ユーザプログラムが出力したログ（`rospy.loginfo`などの出力）です |

1. 対象のシミュレーション結果を開きます。
2. `[DOWNLOAD LOG FILES]` をクリックして、ファイルをダウンロードします。
3. ダウンロードしたファイルを保存します。
4. 結果ファイル（JSON）を開き、シミュレーション結果が記録されていることを確認します。

> [!NOTE]
> 実行結果画面から取得できるのは、上記の結果ファイル（JSON）とユーザプログラムが出力したログのみです。システムログ、シミュレータログ、通信ログ、センサデータなどは提供されません。
> 通信やセンサデータを取得したい場合はrosbagを使用してください。  
> rosbagは、ROS (Robot Operating System) の標準的なデータ記録ツールで、シミュレータ内の各種トピックのデータを記録・再生することができます。

#### 結果ファイル（JSON）の構成

| 項目 | 説明 |
|---|---|
| `Illegal` | 実行が違反扱いとなったかどうか |
| `JudgeReport.mission` | ミッションの開始・終了状態、開始時刻、終了時刻、実行時間 |
| `JudgeReport.checkpoint_detail` | 各チェックポイントの番号、成否、レベル、通過時刻、理由 |
| `JudgeReport.goal` | ゴールの成否、判定理由、到達時刻 |
| `JudgeReport.events` | ミッション開始、チェックポイント通過、ミッション終了などのイベント履歴 |

```json
{
  "Illegal": false,
  "JudgeReport": {
    "mission": {
      "started": true,
      "finished": true,
      "start": "19700101 000010160",
      "finish": "19700101 000505490",
      "duration_sec": 295.33
    },
    "checkpoint_detail": [
      {
        "checkpoint_id": 2,
        "success": true,
        "level": 3,
        "timestamp": "19700101 000125491",
        "reason": "checkpoint validated"
      }
    ],
    "goal": {
      "success": true,
      "reason": "goal checkpoint previously passed",
      "timestamp": "19700101 000505490"
    },
    "events": [
      {
        "status": "Mission Start",
        "timestamp": "19700101 000010160"
      },
      {
        "status": "Mission Finish",
        "timestamp": "19700101 000505490"
      }
    ]
  }
}
```

## 4.4 ローカルシミュレータ

### 4.4.1 ローカルシミュレータの位置づけ

ローカルシミュレータは、開発中の反復確認とデバッグを主な目的とします。基本的な動作確認はローカルシミュレータで行い、最終的な動作確認はWebシミュレータで行ってください。

> [!NOTE]
> 一般的な PC は x86_64 の CPU アーキテクチャを使用しています。  
> 一方、Int-Ball2 実機は Jetson TX2 を搭載しており、CPU アーキテクチャは ARM64 (aarch64) です。  
> そのため、CPU アーキテクチャの違いによって、プログラムの動作、処理速度、利用できるライブラリなどが実機と異なる可能性があります。
> 
> Webシミュレータでは、実機に近い条件で確認できるよう、ARM64 の実行環境を採用しています。ただし、Webシミュレータと実機の動作が完全に一致することを保証するものではありません。

### 4.4.2 動作環境

ローカルシミュレータの実行に必要な CPU、メモリ、ストレージ、OS の条件は、[2.2.1 ローカルシミュレータ実行時の動作環境](#221-ローカルシミュレータ実行時の動作環境)を参照してください。  
ローカルシミュレータは Docker コンテナ内で実行されます。

> [!WARNING]
> x86_64 の PC 上で Docker イメージをビルドして実行する場合、Int-Ball2 実機の ARM64 環境とは CPU アーキテクチャが異なります。アーキテクチャに依存するライブラリや処理を使用する場合は、Webシミュレータまたは実機に近い ARM64 環境でも動作を確認してください。

### 4.4.3 Docker イメージのビルド

ローカルシミュレータは、ホスト環境にシミュレータ本体を個別にインストールするのではなく、Docker イメージをビルドして実行します。Docker のインストール方法は、[2.4.2 Docker のインストール](#242-docker-のインストール)を参照してください。

```bash
cd ~/krpc/krpc7th-simulator
bash ./build.sh
```

`build.sh` は以下のオプションを指定できます。

| オプション | 説明 |
|---|---|
| `--no-cache` | キャッシュを使用せずにビルドします。 |
| `--arm64` | QEMUエミュレーションを用いて、ARM64向けのローカルシミュレータイメージをビルドします（`PLATFORM=linux/arm64`、`BASE_TAG=bionic-arm64`）。Webシミュレータや実機に近い条件の確認に利用できます。 |
| `--platform=<platform>` | ビルド対象のプラットフォームを明示的に指定します（例: `--platform=linux/amd64`）。 |

> [!TIP]
> 利用している PC の CPU アーキテクチャが arm64 の場合は、`--arm64` オプションを付けてビルドしてください。
>
> ```bash
> bash ./build.sh --arm64
> ```

ビルドした Docker イメージが正常に作成されたことを確認してください。

```bash
docker images
```

期待結果

```bash
REPOSITORY          TAG     IMAGE ID      CREATED     SIZE
krpc/krpc-simulator latest  5873e10aa5ee  5 days ago  6.29GB
```

### 4.4.4 シミュレーションの実行

```bash
cd ~/krpc/krpc7th-simulator
bash ./simulation.sh
```

### 4.4.5 実行中のシミュレーションの確認

任意のブラウザでローカルシミュレータの動作を確認できます。
通常、ローカルシミュレータは `http://localhost` でアクセスできます。

> [!TIP]
> 上記の URL でアクセスできない場合、利用中のPCで、別のアプリケーションが HTTP ポートを利用していないか、確認してください。
> もし、利用している場合は、`docker-compose.yaml` で任意のポートに変更してください。

### 4.4.6 シミュレーションの停止

停止する場合は、実行中のターミナルで `Ctrl + C` を押してください。
または、ゲームが完了すると自動で停止します。

# 5. プログラムのヒント

## 5.1 無限ループを避ける

- ループ回数に上限を設定します。
- 処理時間に上限を設定します。
- 終了条件を複数用意します。
- API失敗時のリトライ回数を制限します。

> [!TIP]
> ループの途中で終了条件を複数持つと、処理の安全性が向上します。特に外部通信では、タイムアウトと再試行回数の両方を制限するのが基本です。

## 5.2 エラー処理

以下を考慮します。

- `null` チェック
- 戻り値の確認
- 例外処理
- タイムアウト
- 通信切断
- センサデータ欠損
- 異常値
- リトライ上限
- 安全な終了処理

## 5.3 ログ設計

### 推奨するログ項目

- 処理開始・終了
- アプリケーション版数
- 実行プラン
- API名と実行結果
- 目標位置・姿勢
- 現在位置・姿勢
- センサ値
- エラーコード
- リトライ回数
- 処理時間

### ログレベル

| レベル | 用途 |
|---|---|
| ERROR | 処理を継続できない問題 |
| WARN | 継続可能だが確認が必要な状態 |
| INFO | 通常の処理経過 |
| DEBUG | 開発時の詳細確認 |

## 5.4 処理時間とタイムアウト

- 各処理の開始時刻と終了時刻を記録します。
- 外部応答を待ち続けないようにします。
- ミッション全体の残り時間を確認します。
- 画像処理や推論処理の最大時間を計測します。

## 5.5 移動処理

- 移動前に目標位置と姿勢を確認します。
- 移動結果を必ず確認します。
- 失敗時の再試行回数を制限します。
- 飛行可能領域、機体寸法を考慮します。
- 位置決め完了後に必要な待機時間を設けます。

## 5.6 センサデータの取り扱い

- センサ値を取得できない場合を想定します。
- タイムスタンプを確認します。
- 古いデータを使用しないようにします。
- 単位と座標系を明記します。

## 5.7 画像処理

- 入力画像のサイズ、形式、チャンネル数を確認します。
- 明るさ、反射、ぼけ、ノイズ、歪みを考慮します。

## 5.8 例外処理とリトライ

- 例外発生時に現在の処理状態を確定させます。
- エラー内容をログに残し、次の処理へ影響しないようにします。
- リトライは、再試行の理由と再試行回数を明示した上で実施します。
- 失敗が確定した場合は、送信停止や安全移動などの保護動作に切り替えます。

## 5.9 計算リソース

- 不要なオブジェクトを保持し続けないようにします。
- 大きな画像や配列の複製を避けます。
- 長時間処理は分割または簡略化を検討します。

## 5.10 数値変換と丸め処理

- 単位変換時に丸め誤差を考慮します。
- 端数処理のルールを明確にします。
- 型変換でオーバーフローしないか確認します。
- 近似計算の誤差が連続計算に影響しないか確認します。

## 5.11 並列処理とスレッド

- 共有データへの同時アクセスを避けます。
- スレッド終了条件を明確にします。
- バッファやキューのサイズ上限を設定します。
- スレッド停止時に後片付けを行い、リソース漏れを防ぎます。

## 5.12 データ整合性と境界値確認

- 入力値が許容範囲内か検証します。
- 時刻の境界値、座標の極値、閾値の近傍を確認します。
- 外部依存の値が変化したときの状態を検証します。
- 実行環境ごとの差異が結果に影響しないか比較します。

## 5.13 ARマーカーの認識

ARマーカーを認識する場合は、カメラ画像からマーカーのIDと四隅の画素座標を検出し、カメラの内部パラメータを使ってマーカーの位置・姿勢を推定します。本節では、OpenCV 3.3.1のArUcoモジュールを使用します。

### 5.13.1 推定に必要な情報

以下の値を、画像を取得するカメラの条件に合わせて用意します。

| 情報 | 内容 |
|---|---|
| 入力画像 | 検出時の解像度、画像形式、チャンネル数を確認します。 |
| ArUco辞書 | マーカーのIDとパターンを定義する辞書です。使用するマーカーと一致させます。KRPC 7thでは4×4の辞書を使用します。 |
| マーカーID | 検出後に対象マーカーを識別する番号です。KRPC 7thでは1から12のIDを使用します。 |
| マーカー一辺の長さ | 実寸の長さをメートルで指定します。画像上の大きさではありません。KRPC 7thでは 2cm(0.02m) を使用します。 |
| カメラ行列 | 焦点距離と主点を含む3×3行列です。 |
| 歪み係数 | レンズ歪みの係数です。キャリブレーション結果の順序を維持します。 |

カメラ行列 $K$ は次の形式です。

$$
K = \begin{bmatrix}
f_x & 0 & c_x \\
0 & f_y & c_y \\
0 & 0 & 1
\end{bmatrix}
$$

`/camera_main/camera_info`を利用する場合は、`CameraInfo.K`をカメラ行列、`CameraInfo.D`を歪み係数として使用します。画像をリサイズする場合は、$f_x$、$f_y$、$c_x$、$c_y$も同じ倍率で変更してください。画像を切り出す場合は主点の補正も必要です。

### 5.13.2 検出と姿勢推定の手順

1. カメラ画像をグレースケールに変換します。
2. 使用するArUco辞書と検出パラメータを作成します。
3. `detectMarkers`でマーカーIDと四隅の画素座標を検出します。
4. 対象IDを選択し、マーカー一辺の実寸、カメラ行列、歪み係数を指定して姿勢を推定します。
5. 距離、姿勢の変化、再投影結果を確認し、必要なら複数フレームで安定性を確認します。

`estimatePoseSingleMarkers`が返す`rvec`と`tvec`は、マーカー座標系からカメラ座標系への変換です。`tvec`の単位はマーカー一辺の長さと同じなので、長さをメートルで指定すればメートルになります。通常のOpenCVカメラ座標系では、画像の右方向がX、画像の下方向がY、カメラ前方がZです。`iss_body`や`body`座標系へ変換する場合は、カメラの取り付け姿勢を使って別途変換してください。

> [!WARNING]
> 辞書、マーカーID、マーカー一辺の長さ、カメラ行列、歪み係数のいずれかが検出対象と異なると、検出できても距離や姿勢が誤ります。特にマーカー一辺の長さをピクセル値で指定しないでください。

#### Int-Ball2のカメラの取り付け位置

カメラはInt-Ball2の前方に取り付けられており、光軸は機体の前方と一致しています。カメラの取り付け位置と姿勢は、Int-Ball2の前方（x軸正方向）、左方（y軸正方向）、上方（z軸正方向）を基準に以下のように定義されます。

```python
x = 0.14  # 前方へのオフセット（メートル）
y = 0.00
z = 0.00
```

# 6. Game APIの詳細

## 6.1 API利用時の共通事項

本章では、ユーザプログラムから利用するROSインターフェースを扱います。呼び出し方法はROS Service、ROS Action、ROS Topic、ROS Parameterに分かれます。

本章では、Topicの型を「メッセージ型」、Serviceの型を「サービス型」、Actionの元になる`.action`ファイルを「アクション定義」と呼び分けます。`.srv`定義からはサービス型とRequest/Responseメッセージ型が生成されます。Actionは単一のメッセージ型ではなく、`.action`定義からActionクライアント用の型、Goal・Result・Feedbackのメッセージ型、Action通信を構成するメッセージ型が生成され、それらを使って通信します。Actionクライアントの生成時には`...Action`型を指定し、送信する目標には`...Goal`型を使います。

API一覧では、パッケージ名と定義ファイル名を分けて示します。実装時に使うPythonの型やC++のヘッダ／型は、[6.2.5 定義ファイルごとの実装参照（Python／C++）](#625-定義ファイルごとの実装参照pythonc)を確認してください。ROS Parameterには定義ファイルがありません。

- ROS Serviceは、要求を送信して応答を受け取る処理に使用します。
- ROS Actionは、移動など時間のかかる処理に使用します。サーバ接続、完了待ち、結果確認を行います。
- ROS Topicは、自己位置のように継続的に配信されるデータの購読に使用します。
- ROS Parameterは、ユーザプログラムの設定値の取得や変更に使用します。
- 通信相手が起動していることを確認してから呼び出します。
- ROS Actionは必ずタイムアウト、キャンセル、ROS終了時の処理を設計します。

## 6.2 API一覧

### 6.2.1 ミッションイベントAPI

| ROS Namespace | ROS種別 | パッケージ | 定義ファイル | 用途 |
|---|---|---|---|---|
| /mission/get_checkpoints | Service | `krpc_ib2_msgs` | `CheckPoints.srv` | チェックポイント定義を取得する |
| /event/mission_start | Service | `krpc_ib2_msgs` | `MissionStart.srv` | ミッション開始を通知する |
| /event/checkpoint_passed | Action | `krpc_ib2_msgs` | `CheckpointPassed.action` | チェックポイント到達を通知する |
| /event/mission_finished | Service | `krpc_ib2_msgs` | `MissionFinished.srv` | ミッション完了を通知する |

### 6.2.2 自己位置・移動API

| ROS Namespace | ROS種別 | パッケージ | 定義ファイル | 用途 |
|---|---|---|---|---|
| /sensor_fusion/navigation | Topic | `ib2_msgs` | `Navigation.msg` | 自己位置、姿勢、速度などを購読する |
| /ctl/command | Action | `ib2_msgs` | `CtlCommand.action` | 絶対移動、相対移動、停止、ドッキングなどを要求する |
| /ctl/wrench | Topic | `geometry_msgs` | `WrenchStamped.msg` | Int-Ball2に直接並進力（force）、回転トルク（torque）を加えて制御する。Actionの`/ctl/command`を使用するよりシームレスに動けるが難度は上がる |
| /ctl/status | Topic | `ib2_msgs` | `CtlStatus.msg` | Int-Ball2の現在の制御ステータスを取得できる |

### 6.2.3 カメラAPI

| ROS Namespace | ROS種別 | パッケージ | 定義ファイル | 用途 |
|---|---|---|---|---|
| /camera_main/image_raw | Topic | `sensor_msgs` | `Image.msg` | メインカメラの画像を購読する |
| /camera_main/camera_info | Topic | `sensor_msgs` | `CameraInfo.msg` | メインカメラの内部パラメータ（焦点距離、歪み係数など）を取得する |

### 6.2.4 ユーザプログラム制御API

| ROS Namespace | ROS種別 | パッケージ | 定義ファイル／値型 | 用途 |
|---|---|---|---|---|
| /ib2_user/start | Topic | `platform_msgs` | `UserLogic.msg` | ユーザプログラムの実行開始通知を購読する（購読必須） |
| /ib2_user/stop | Service | `platform_msgs` | `StopProcessingUserNode.srv` | ユーザプログラムへの停止要求を受け付ける（実機実装時は提供必須） |
| /ib2_user/ready | Parameter | - | `bool`（定義ファイルなし） | ユーザプログラムの準備完了を通知する（設定必須） |

### 6.2.5 定義ファイルごとの実装参照（Python／C++）

定義ファイルから生成される型と、Python／C++での利用方法を示します。完全な定義パスは「パッケージ名/種別ディレクトリ/定義ファイル名」です。Actionは`.action`を直接importするのではなく、生成された`Action`型と`Goal`型を使います。

#### 6.2.5.1 Python

- **krpc_ib2_msgs/srv/CheckPoints.srv**

  ```python
  from krpc_ib2_msgs.srv import CheckPoints
  client = rospy.ServiceProxy('/mission/get_checkpoints', CheckPoints)
  ```

- **krpc_ib2_msgs/srv/MissionStart.srv**

  ```python
  from krpc_ib2_msgs.srv import MissionStart
  client = rospy.ServiceProxy('/event/mission_start', MissionStart)
  ```

- **krpc_ib2_msgs/action/CheckpointPassed.action**

  ```python
  import actionlib
  from krpc_ib2_msgs.msg import CheckpointPassedAction, CheckpointPassedGoal

  client = actionlib.SimpleActionClient('/event/checkpoint_passed', CheckpointPassedAction)
  goal = CheckpointPassedGoal()
  ```

- **krpc_ib2_msgs/srv/MissionFinished.srv**

  ```python
  from krpc_ib2_msgs.srv import MissionFinished
  client = rospy.ServiceProxy('/event/mission_finished', MissionFinished)
  ```

- **ib2_msgs/msg/Navigation.msg**

  ```python
  from ib2_msgs.msg import Navigation
  sub = rospy.Subscriber('/sensor_fusion/navigation', Navigation, callback)
  ```

- **ib2_msgs/action/CtlCommand.action**

  ```python
  import actionlib
  from ib2_msgs.msg import CtlCommandAction, CtlCommandGoal, CtlStatusType

  client = actionlib.SimpleActionClient('/ctl/command', CtlCommandAction)
  goal = CtlCommandGoal()
  ```

- **geometry_msgs/msg/WrenchStamped.msg**

  ```python
  from geometry_msgs.msg import WrenchStamped
  pub = rospy.Publisher('/ctl/wrench', WrenchStamped, queue_size=1)
  ```

- **ib2_msgs/msg/CtlStatus.msg**

  ```python
  from ib2_msgs.msg import CtlStatus
  sub = rospy.Subscriber('/ctl/status', CtlStatus, callback)
  ```

- **sensor_msgs/msg/Image.msg**

  ```python
  from sensor_msgs.msg import Image
  sub = rospy.Subscriber('/camera_main/image_raw', Image, callback)
  ```

- **sensor_msgs/msg/CameraInfo.msg**

  ```python
  from sensor_msgs.msg import CameraInfo
  sub = rospy.Subscriber('/camera_main/camera_info', CameraInfo, callback)
  ```

- **platform_msgs/msg/UserLogic.msg**

  ```python
  from platform_msgs.msg import UserLogic
  sub = rospy.Subscriber('/ib2_user/start', UserLogic, callback)
  ```

- **platform_msgs/srv/StopProcessingUserNode.srv**

  ```python
  from platform_msgs.srv import StopProcessingUserNode, StopProcessingUserNodeResponse
  server = rospy.Service('/ib2_user/stop', StopProcessingUserNode, callback)
  ```

- **ROS Parameter（定義ファイルなし）**

  ```python
  rospy.set_param('/ib2_user/ready', True)
  ```

#### 6.2.5.2 C++

- **krpc_ib2_msgs/srv/CheckPoints.srv**

  ```cpp
  #include <krpc_ib2_msgs/CheckPoints.h>

  ros::ServiceClient client = nh.serviceClient<krpc_ib2_msgs::CheckPoints>("/mission/get_checkpoints");
  krpc_ib2_msgs::CheckPoints service;
  client.call(service);
  ```

- **krpc_ib2_msgs/srv/MissionStart.srv**

  ```cpp
  #include <krpc_ib2_msgs/MissionStart.h>

  ros::ServiceClient client = nh.serviceClient<krpc_ib2_msgs::MissionStart>("/event/mission_start");
  krpc_ib2_msgs::MissionStart service;
  client.call(service);
  ```

- **krpc_ib2_msgs/action/CheckpointPassed.action**

  ```cpp
  #include <actionlib/client/simple_action_client.h>
  #include <krpc_ib2_msgs/CheckpointPassedAction.h>
  #include <krpc_ib2_msgs/CheckpointPassedGoal.h>

  actionlib::SimpleActionClient<krpc_ib2_msgs::CheckpointPassedAction> client("/event/checkpoint_passed", true);
  krpc_ib2_msgs::CheckpointPassedGoal goal;
  client.sendGoal(goal);
  ```

- **krpc_ib2_msgs/srv/MissionFinished.srv**

  ```cpp
  #include <krpc_ib2_msgs/MissionFinished.h>

  ros::ServiceClient client = nh.serviceClient<krpc_ib2_msgs::MissionFinished>("/event/mission_finished");
  krpc_ib2_msgs::MissionFinished service;
  client.call(service);
  ```

- **ib2_msgs/msg/Navigation.msg**

  ```cpp
  #include <ib2_msgs/Navigation.h>

  ros::Subscriber sub = nh.subscribe<ib2_msgs::Navigation>("/sensor_fusion/navigation", 1, callback);
  ```

- **ib2_msgs/action/CtlCommand.action**

  ```cpp
  #include <actionlib/client/simple_action_client.h>
  #include <ib2_msgs/CtlCommandAction.h>
  #include <ib2_msgs/CtlCommandGoal.h>
  #include <ib2_msgs/CtlStatusType.h>

  actionlib::SimpleActionClient<ib2_msgs::CtlCommandAction> client("/ctl/command", true);
  ib2_msgs::CtlCommandGoal goal;
  client.sendGoal(goal);
  ```

- **geometry_msgs/msg/WrenchStamped.msg**

  ```cpp
  #include <geometry_msgs/WrenchStamped.h>

  ros::Publisher pub = nh.advertise<geometry_msgs::WrenchStamped>("/ctl/wrench", 1);
  ```

- **ib2_msgs/msg/CtlStatus.msg**

  ```cpp
  #include <ib2_msgs/CtlStatus.h>

  ros::Subscriber sub = nh.subscribe<ib2_msgs::CtlStatus>("/ctl/status", 1, callback);
  ```

- **sensor_msgs/msg/Image.msg**

  ```cpp
  #include <sensor_msgs/Image.h>

  ros::Subscriber sub = nh.subscribe<sensor_msgs::Image>("/camera_main/image_raw", 1, callback);
  ```

- **sensor_msgs/msg/CameraInfo.msg**

  ```cpp
  #include <sensor_msgs/CameraInfo.h>

  ros::Subscriber sub = nh.subscribe<sensor_msgs::CameraInfo>("/camera_main/camera_info", 1, callback);
  ```

- **platform_msgs/msg/UserLogic.msg**

  ```cpp
  #include <platform_msgs/UserLogic.h>

  ros::Subscriber sub = nh.subscribe<platform_msgs::UserLogic>("/ib2_user/start", 1, callback);
  ```

- **platform_msgs/srv/StopProcessingUserNode.srv**

  ```cpp
  #include <platform_msgs/StopProcessingUserNode.h>

  ros::ServiceServer server = nh.advertiseService("/ib2_user/stop", callback);
  ```

- **ROS Parameter（定義ファイルなし）**

  ```cpp
  ros::param::set("/ib2_user/ready", true);
  ```

C++テンプレート全体は`users/catkin_ws/src/krpc_user/src/user_template_node.cpp`を参照してください。

`/ib2_user/start`、`/ib2_user/stop`、`/ib2_user/ready`は、テンプレートに実装済みの必須インターフェースです。削除や無効化をしないでください。

## 6.3 API詳細

### 6.3.1 ミッションイベントAPI

#### /mission/get_checkpoints

チェックポイント定義を取得します。Requestは空で、Responseの`message`にJSON文字列が返ります。

##### サービス定義

- CheckPoints.srv

```text
# Empty request

---
bool success
string message
```

##### レスポンス例

```json
{
  "checkpoint_count": 8,
  "checkpoints": [
    {
      "checkpoint_id": 1,
      "position": [1.4421152111823452, -0.5013235815457989, 0.6649623093633403],
      "marker_pose": {
        "position": [1.451, -1.001, 0.6806],
        "quaternion": [-0.707106781187, 0.0, 0.0, 0.707106781187]
      },
      "score_bands": [
        { "radius": 0.1, "level": 3 },
        { "radius": 0.2, "level": 2 },
        { "radius": 0.3, "level": 1 }
      ],
      "attitude": {
        "quaternion": [0.705928907230986, -0.689998801417597, 0.12254331978784033, -0.10270913665940805],
        "centering_bands": [
          { "angle": 10.0, "level": 3 },
          { "angle": 20.0, "level": 2 },
          { "angle": 30.0, "level": 1 }
        ],
        "roll_bands": [
          { "angle": 10.0, "level": 3 },
          { "angle": 20.0, "level": 2 },
          { "angle": 30.0, "level": 1 }
        ]
      }
    },
    ...
  ],
  "goalpoint_id": 12
}
```

> [!NOTE]
> 上記は`checkpoints`配列の1件目のみを抜粋した例です。実際のレスポンスでは、`checkpoints`に`checkpoint_count`件の要素が同じ形式で並びます。

チェックポイント通過時は、次の3条件を個別に判定します。各条件にはLv1～Lv3のマージンが設定され、条件ごとの判定レベルのうち最も低いレベルが総合評価レベルになります。いずれかの条件がマージン外の場合は通過失敗です。

- **位置**：機体と`position`で指定されたチェックポイント座標との距離を`score_bands`で判定します。
- **カメラのセンタリング**：機体のカメラ視線方向と、機体からARマーカーへ向かう方向の角度を`attitude.centering_bands`で判定します。マーカーを画像中央付近に捉える条件です。
- **視線軸回りの姿勢**：`attitude.quaternion`で指定された目標姿勢に対し、カメラ視線方向を軸とした回転角度の差を`attitude.roll_bands`で判定します。

姿勢条件はレスポンスの`attitude`に各bandが定義されている場合に判定されます。各マージンとレベルの対応は、レスポンスに含まれるband定義を参照してください。

#### /event/mission_start

ミッション開始を通知します。Requestは空です。

##### サービス定義

- MissionStart.srv

```text
---
bool success
string message
```

#### /event/checkpoint_passed

指定したチェックポイントの通過判定をサーバに依頼するActionです。移動Actionの成功だけでは通過は確定しません。3つの判定条件を満たし、機体が安定したことを確認してから送信してください。サーバが現在の状態を評価し、Resultの`success`に判定結果を返します。

##### アクション定義

- CheckpointPassed.action

```text
# Goal
int32 checkpoint_id

---
# Result
bool success
string message

---
# Feedback
string status
```

この`.action`定義から、Actionクライアント用の`CheckpointPassedAction`型と、目標・結果・フィードバック用の`CheckpointPassedGoal`、`CheckpointPassedResult`、`CheckpointPassedFeedback`型が生成されます。さらに、Action通信を構成する`CheckpointPassedActionGoal`、`CheckpointPassedActionResult`、`CheckpointPassedActionFeedback`型も生成されます。PythonではActionクライアントに`CheckpointPassedAction`を指定し、送信するGoalを`CheckpointPassedGoal`で作成します。`CheckpointPassed*`は型名ではなく、関連する生成型をまとめて示す説明用の略記です。

#### /event/mission_finished

ミッション完了を通知します。

##### サービス定義

- MissionFinished.srv

```text
# Empty request

---
bool success
string message
```

### 6.3.2 自己位置・移動API

#### /sensor_fusion/navigation

自己位置、姿勢、速度、加速度を継続的に取得するTopicです。

##### メッセージ定義

- Navigation.msg

```text
geometry_msgs/PoseStamped pose
geometry_msgs/Twist twist
geometry_msgs/Vector3 a
NavigationStatus status
```

#### /ctl/command

目標位置・姿勢を指定して、移動や停止などの制御を要求します。

##### アクション定義

- CtlCommand.action

```text
# Goal
geometry_msgs/PoseStamped target
CtlStatusType type

---
# Result
uint8 TERMINATE_SUCCESS = 0
uint8 TERMINATE_ABORTED = 1
uint8 TERMINATE_TIME_OUT = 2
uint8 TERMINATE_INVALID_NAV = 3
uint8 TERMINATE_INVALID_CMD = 4
time stamp
uint8 type

---
# Feedback
duration time_to_go
geometry_msgs/Pose pose_to_go
```

この`.action`定義から、Actionクライアント用の`CtlCommandAction`型や、Goal・Result・Feedback用の型が生成されます。PythonではActionクライアントに`CtlCommandAction`を指定し、目標を`CtlCommandGoal`で作成します。

主な`CtlStatusType`は`MOVE_TO_ABSOLUTE_TARGET`、`MOVE_TO_RELATIVE_TARGET`、`STOP_MOVING`です。

##### CtlStatusTypeについて

| 種別 | 説明 | `target`の指定 | 備考 |
|---|---|---|---|
| `MOVE_TO_ABSOLUTE_TARGET` | ISS基準座標系（`iss_body`）での絶対位置・姿勢への移動 | 絶対座標・姿勢を指定 | `frame_id`は`iss_body` |
| `MOVE_TO_RELATIVE_TARGET` | 機体座標系（`body`）を基準とした相対位置・姿勢への移動 | 現在位置からの相対座標・姿勢を指定 | `frame_id`は`body` |
| `STOP_MOVING` | 実行中の移動を減速して停止し、その場で姿勢を保持する | 指定不要（`0`埋めで送信） | 停止後は`KEEP_POSE`相当の状態になる |

> [!NOTE]
> 上記以外に、待機状態を表す`STAND_BY`・`KEEP_POSE`や、マーカー補正を行わないドッキングを指定する`DOCK_WITHOUT_CORRECTION`もサーバ内部の状態として存在しますが、ユーザプログラムから目標として指定するのは主に上記3種類です。

##### 移動のキャンセル

移動中に再計画や停止が必要になった場合は、Actionクライアントの`cancel_goal()`を使用します。キャンセル要求後は、Actionの終了または停止完了を確認してから次の目標を送信します。

###### Python実装例

```python
command_client.cancel_goal()
if not command_client.wait_for_result(rospy.Duration(10.0)):
    rospy.logwarn('cancel did not complete')
```

#### /ctl/wrench

Int-Ball2に直接`force`（並進力）と`torque`（回転トルク）を加えて制御するTopicです。`/ctl/command`（Action）を使用するよりシームレスに機体を動かせますが、目標位置・姿勢への到達や停止をユーザプログラム側で管理する必要があるため、難度は上がります。

##### メッセージ定義

`/ctl/wrench`は標準の`geometry_msgs/WrenchStamped`メッセージ型を使用します。

- WrenchStamped.msg

```text
Header header
Wrench wrench
```

- Wrench.msg

```text
Vector3 force
Vector3 torque
```

> [!NOTE]
> `force`は機体座標系（`body`）における並進力[N]、`torque`は同座標系における回転トルク[Nm]です。
> `/ctl/command`による移動中に`/ctl/wrench`を送信すると、機体の状態遷移によっては意図しない挙動になる場合があるため、両者を同時に使用する場合は状態遷移を十分に確認してください。

#### /ctl/status

Int-Ball2の現在の制御ステータス（位置・姿勢・速度・加速度・制御状態）を継続的に取得するTopicです。

##### メッセージ定義

- CtlStatus.msg

```text
geometry_msgs/PoseStamped pose
geometry_msgs/Twist twist
geometry_msgs/Vector3 a
CtlStatusType type
```

- CtlStatusType.msg

```text
int32 STAND_BY                  =  0
int32 CAPTURED                  =  1
int32 DISTURBED                 =  2
int32 KEEP_POSE                 = 10
int32 KEEPING_POSE_BY_COLLISION = 11
int32 STOP_MOVING               = 20
int32 MOVE_TO_RELATIVE_TARGET   = 30
int32 MOVE_TO_ABSOLUTE_TARGET   = 40
int32 RELEASE                   = 50
int32 DOCK                      = 60
int32 MOVING_TO_AIA_AIP         = 61
int32 WAITING_AT_AIA_AIP        = 62
int32 MOVING_TO_RDA_AIP         = 63
int32 MOVING_TO_RDP             = 64
int32 DOCKING_STAND_BY          = 65
int32 DOCK_WITHOUT_CORRECTION   = 69
int32 SCAN                      = 70

int32 type
```

> [!NOTE]
> `type`は`/ctl/command`で指定した`CtlStatusType`に対応する現在の制御状態を表します。`MOVE_TO_ABSOLUTE_TARGET`や`MOVE_TO_RELATIVE_TARGET`などの移動系状態から`KEEP_POSE`や`STOP_MOVING`に遷移したかを確認することで、移動の完了や中断をポーリングで確認できます。

### 6.3.3 カメラAPI

#### /camera_main/image_raw

メインカメラの画像を継続的に配信するTopicです。ROS標準の`sensor_msgs/Image`を使用します。

> [!TIP]
> 画像認識にOpenCVを使用する場合は、`cv_bridge`または`ros_numpy`で`sensor_msgs/Image`をOpenCV形式に変換してください。

##### メッセージ定義

> [!NOTE]
> ROS標準の`sensor_msgs/Image`メッセージ型を使用します。ここでは主要なフィールドを示します。

- Image.msg

```text
std_msgs/Header header
uint32 height
uint32 width
string encoding
uint8 is_bigendian
uint32 step
uint8[] data
```

#### /camera_main/camera_info

メインカメラの内部パラメータを配信するTopicです。ROS標準の`sensor_msgs/CameraInfo`を使用します。

##### メッセージ定義

> [!NOTE]
> ROS標準の`sensor_msgs/CameraInfo`メッセージ型を使用します。ここでは主要なフィールドを示します。

- CameraInfo.msg

```text
std_msgs/Header header
uint32 height
uint32 width
string distortion_model
float64[] D
float64[9] K
float64[9] R
float64[12] P
```
> [!TIP]
> `K`はカメラ行列、`D`は歪み係数です。ARマーカー検出など、カメラ座標系での姿勢推定を行う場合に使用します。
> 保持している`CameraInfo`オブジェクトは、最初のメッセージを受信するまで`None`のままです。`K`や`D`を参照する前に、受信済みかを確認してください。

### 6.3.4 ユーザプログラム制御API

#### /ib2_user/start

ユーザプログラムの実行開始をテンプレートへ通知するTopicです。
このTopicの購読処理はテンプレートに実装済みで、削除してはいけません。二重起動を避けるため、コールバック内で開始済みかどうかを判定します。

##### メッセージ定義

- UserLogic.msg

```text
uint16 id
```

#### /ib2_user/stop

ユーザプログラムへの停止要求を受け付けるServiceです。

##### サービス定義

- StopProcessingUserNode.srv

```text
# Empty request

---
uint8 SUCCESS = 0
uint8 ERROR = 255
uint8 result
```

> [!CHECK]
> 停止要求を受けたら、実行中のActionをキャンセルしてから応答します。応答を返さないとテンプレート側の停止処理が完了しません。
> 実装例はテンプレートの`__stop_processing`メソッドを参照してください。

#### /ib2_user/ready

ユーザプログラムの初期化完了を通知するROS Parameterです。

##### Python設定例

```python
rospy.set_param('/ib2_user/ready', True)
```

> [!CHECK]
> この設定はテンプレートに実装済みで、削除してはいけません。`/ib2_user/ready`が`true`になるまで、`/ib2_user/start`のイベントは発行されません。

## 6.4 サンプルソースコード

完全なサンプル実装は`users/catkin_ws/src/krpc_user/scripts/user_template.py`にあります。全体像はそちらを参照してください。本節では、6.2・6.3で紹介した各APIを、このテンプレートがどのように利用しているかを解説します。

> [!NOTE]
> 本節のコード例はAPIの基本的な使い方を示す簡略例であり、実運用に必要なエラー処理をすべて含むものではありません。たとえば、掲載した`wait_for_service()`および`wait_for_server()`にはタイムアウトがなく、停止要求の例では移動Actionのみを追跡・キャンセルします。実運用では6.5の方針に従い、各待機に有限のタイムアウトを設け、実行中のすべてのActionを追跡してキャンセルし、停止完了を確認してから応答してください。

### 6.4.1 初期化（`__init__`）

コンストラクタで、ミッションイベントAPIと移動APIのクライアント、および`/ib2_user/start`・`/ib2_user/stop`・`/ib2_user/ready`の必須インターフェースをまとめて用意します。

```python
# Action client
self.__command = actionlib.SimpleActionClient('/ctl/command', CtlCommandAction)
self.__checkpoint_client = actionlib.SimpleActionClient('/event/checkpoint_passed', CheckpointPassedAction)

# Service client
self.__mission_start = rospy.ServiceProxy('/event/mission_start', MissionStart)
self.__mission_finished = rospy.ServiceProxy('/event/mission_finished', MissionFinished)
self.__checkpoints = rospy.ServiceProxy('/mission/get_checkpoints', CheckPoints)

# Subscriber
self.__subscriber_start = rospy.Subscriber('/ib2_user/start', UserLogic, self.__callback_start)  # DO NOT REMOVE THIS LINE

# Service server
self.__stop_processing_server = rospy.Service('/ib2_user/stop', StopProcessingUserNode, self.__stop_processing) # DO NOT REMOVE THIS LINE

self.__started = False
self.__action_active = False
rospy.set_param('/ib2_user/ready', True) # DO NOT REMOVE THIS LINE
```

`/ib2_user/start`の購読、`/ib2_user/stop`のサービス提供、`/ib2_user/ready`の設定は、コメントのとおり削除しないでください。

### 6.4.2 ミッション開始のトリガー（`__callback_start`）

`/ib2_user/start`のコールバックが、ミッションフロー全体の起点です。二重起動を防ぐガードのあと、`__run_user_flow`を呼び出します。

```python
def __callback_start(self, msg):
    if self.__started:
        rospy.logwarn('start callback is already processed')
        return
    self.__started = True

    rospy.loginfo('start %s', msg)
    self.__run_user_flow(msg)
```

### 6.4.3 ミッションフロー全体（`__run_user_flow`）

サンプルでは`__run_user_flow`が、`/event/mission_start` → チェックポイント処理 → `/event/mission_finished`という一連の流れを制御します。  
チーム独自のルート計画や動作判断のロジックは、`USER EDIT AREA`の間に追加してください。

```python
def __run_user_flow(self, msg):
    try:
        if not self.__notify_mission_start():
            return

        # USER EDIT AREA: define route planning and game-specific flow here.
        # ***********************************************
        checkpoint_target = self.__resolve_first_checkpoint_target()
        if not self.__move_to_checkpoint(checkpoint_target):
            return
        if not self.__notify_checkpoint_passed(checkpoint_target['checkpoint_id']):
            return
        # ***********************************************

        if not rospy.is_shutdown():
            self.__notify_mission_finished()
    except Exception as exc:
        rospy.logerr('user flow failed: %s', exc)
```

この例は移動Actionの成功後に通過通知を送る基本フローを示しています。実際のミッションでは、移動成功に加えて機体の安定、カメラ視線のセンタリング、視線軸回りの姿勢条件を満たしたことを確認してから通知してください。通過Lvの判定自体はサーバ側で行われます。

### 6.4.4 ミッションイベントAPIの呼び出し

`/event/mission_start`と`/event/mission_finished`は、`wait_for_service()`で待機してから呼び出し、`success`を確認するだけの薄いラッパーとして実装されています（`__notify_mission_start`・`__notify_mission_finished`）。

```python
def __notify_mission_start(self):
    rospy.wait_for_service('/event/mission_start')
    res = self.__mission_start()
    rospy.loginfo('mission_start result: success=%s message=%s', res.success, res.message)
    return res.success
```

`/mission/get_checkpoints`は`__resolve_first_checkpoint_target`から呼び出され、応答のJSON文字列（`message`）を解析して最初のチェックポイントの`position`と`attitude.quaternion`を移動目標として取得します。これは移動先の位置・姿勢を設定する処理であり、カメラのセンタリングや視線軸回りの姿勢条件を満たしたことを保証するものではありません。取得や解析に失敗した場合は、テンプレートが途中で停止せずに一連の処理（移動→通過通知→ミッション完了）を最後まで実行できるように、既定値として原点への移動を返します。これはテンプレートの動作確認用の仮の値であり、得点にはつながりません。実際のミッションでは、失敗をログに記録したうえで再取得や中断など、意図した処理に置き換えてください。

```python
rospy.wait_for_service('/mission/get_checkpoints')
res = self.__checkpoints()
rospy.loginfo('get_checkpoints result: success=%s message=%s', res.success, res.message)
if not res.success:
    return default_target
```

`/event/checkpoint_passed`は`__notify_checkpoint_passed`で呼び出します。Actionの完了を`wait_for_result(0.2)`のポーリングで待ち、ROS終了時は`cancel_goal()`でキャンセルします。

```python
self.__checkpoint_client.wait_for_server()
goal = CheckpointPassedGoal()
goal.checkpoint_id = checkpoint_id
self.__checkpoint_client.send_goal(goal)
while not rospy.is_shutdown():
    if self.__checkpoint_client.wait_for_result(rospy.Duration(0.2)):
        result = self.__checkpoint_client.get_result()
        rospy.loginfo('checkpoint_passed result: %s', result)
        return result.success
if rospy.is_shutdown():
    self.__checkpoint_client.cancel_goal()
    rospy.logwarn('checkpoint_passed action cancelled by node shutdown')
return False
```

### 6.4.5 `/ctl/command`の呼び出し（`__move_to_checkpoint`）

`__resolve_first_checkpoint_target`で得た位置・姿勢から`PoseStamped`を組み立て、`CtlStatusType.MOVE_TO_ABSOLUTE_TARGET`を指定して`/ctl/command`へ送信します。結果は`CtlCommandResult.TERMINATE_SUCCESS`と比較して判定します。

```python
command_type = CtlStatusType(type=CtlStatusType.MOVE_TO_ABSOLUTE_TARGET)
goal = CtlCommandGoal(target=target, type=command_type)
self.__action_active = True
try:
    self.__command.send_goal(goal)
    while not rospy.is_shutdown():
        if self.__command.wait_for_result(rospy.Duration(0.2)):
            result = self.__command.get_result()
            rospy.loginfo('move command result: %s', result)
            return result.type == CtlCommandResult.TERMINATE_SUCCESS
    if rospy.is_shutdown():
        self.__command.cancel_goal()
        rospy.logwarn('move command cancelled by node shutdown')
    return False
finally:
    self.__action_active = False
```

`self.__action_active`は、`/ib2_user/stop`受信時に実行中のActionをキャンセルするかどうかの判定に使われます。

### 6.4.6 停止要求への対応（`__stop_processing`）

`/ib2_user/stop`を受信すると、移動Actionが実行中であればキャンセルしてから応答を返します。

```python
def __stop_processing(self, request):
    try:
        if self.__action_active:
            self.__command.cancel_goal()
        rospy.loginfo('finish processing')
        return StopProcessingUserNodeResponse(result=StopProcessingUserNodeResponse.SUCCESS)
    except Exception as exc:
        rospy.logerr('stop processing failed: %s', exc)
        return StopProcessingUserNodeResponse(result=StopProcessingUserNodeResponse.ERROR)
```

### 6.4.7 任意API（自己位置・カメラ）の追加方法

`/sensor_fusion/navigation`と`/camera_main/image_raw`は、テンプレートにコメントアウトされた例として用意されています。使用する場合は、該当行のコメントを解除してください。

```python
# self.__subscriber_nav = rospy.Subscriber('/sensor_fusion/navigation', Navigation, self.__callback_nav)
# self.__subscriber_camera = rospy.Subscriber('/camera_main/image_raw', Image, self.__callback_camera_image)
```

### 6.4.8 C++14での実装例

C++14で実装する場合は、`users/catkin_ws/src/krpc_user/src/user_template_node.cpp`に同等のテンプレートがあります。`/ib2_user/start`の購読、`/ib2_user/stop`のサービス、`/ib2_user/ready`の設定、`get_checkpoints`・`/ctl/command`・`checkpoint_passed`・`mission_finished`の呼び出しをactionlibと`ros::ServiceClient`/`ServiceServer`で組み合わせている点はPython版と同じです。

## 6.5 エラー時の基本方針

| 状況 | 対応 |
|---|---|
| Serviceが利用できない | `wait_for_service()`で待機し、上限時間を超えたら終了する |
| Actionサーバが利用できない | `wait_for_server()`で待機し、実行を開始しない |
| 移動が失敗した | 到達通知を送らず、原因をログに記録する |
| Actionがタイムアウトした | `cancel_goal()`を呼び出し、停止完了を確認する |
| `checkpoint_passed`が失敗した | `message`またはResultを記録し、同じ要求を無制限に再送しない |
| カメラ画像やcamera_infoが届かない | 一定のタイムアウトを設けて待ち、期限内に新しいデータが届かない場合はログに記録し、カメラを使う処理をスキップする |
| `/ib2_user/stop`を受信した | 実行中のActionをキャンセルし、安全に処理を終了してから応答する |
