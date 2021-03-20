from flask import Flask, request, jsonify, render_template, redirect, url_for, session

# from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin
import json

# import uuid
import hashlib
import re
from src.database import init_db, db
from src.models import User, LikeUnlike, AnimeData
from requests_oauthlib import OAuth1Session
from urllib.parse import parse_qsl
from flask_cors import CORS
from src.settings import ENV_VALUES
from src.utils import img_encode
from sqlalchemy import desc, asc

import numpy as np

# https://qiita.com/AndanteSysDes/items/a25acc1523fa674e7eda
# https://qiita.com/shirakiya/items/0114d51e9c189658002e
# https://qiita.com/kai_kou/items/5d73de21818d1d582f00
# https://qiita.com/voygerrr/items/4c78d156fc91111798d5


def create_app():
    # twitter api key
    consumer_api_key = ENV_VALUES["CONSUMER_API_KEY"]
    consumer_secret_key = ENV_VALUES["CONSUMER_SECRET_KEY"]
    # Twitter api URLs
    request_token_url = "https://api.twitter.com/oauth/request_token"
    authorization_url = "https://api.twitter.com/oauth/authorize"
    access_token_url = "https://api.twitter.com/oauth/access_token"

    app = Flask(__name__)
    app.config.from_object("src.config.Config")  # configを別ファイルのオブジェクトから読み込む
    CORS(app)

    # login_manager = LoginManager()
    # login_manager.init_app(app)
    app.secret_key = b"\x17x\xf0\x83\x93i\x14\xa3\xec<7\x88A\xca\xb5G"

    init_db(app)  # databaseの初期化を行う

    @app.route("/")
    def index():
        if "user_name" in session:
            # セッション変数の取得
            name = session["user_name"]
            return f"hello {name}"
        else:
            return redirect(url_for("get_twitter_request_token"))

    @app.route("/show")
    def show_users():
        if "user_name" in session:
            all_user = User.query.all()
            number_of_user = len(all_user)
            if not number_of_user == 0:
                user_names_list = [user.name for user in all_user]
                strings = "\n".join(str(user_names_list))
            else:
                strings = ""
            return (
                f'こんにちは{session["user_name"]}. 今ユーザーは{number_of_user}人います. \n' + strings
            )
        else:
            return """ログインしてください.<a href="/login">ログインページ</a>"""

    """
    @app.route('/add')
    def add_user():
        #user = User(name='name', email='test@test.com')
        user = User(name='name')
        db.session.add(user)
        db.session.commit()
        return 'ユーザーを増やしました'

    @app.route('/delete')
    def delete_user():
        user = User.query.first()
        if user is not None:
            db.session.delete(user)
            db.session.commit()
            return 'ユーザーを減らしました'
        else:
            return 'ユーザーはひとりもいません'
    """
    """
    @app.route('/login', methods=['POST', 'GET'])
    def login_test():
        if request.method == 'POST':
            name = request.form['user_name']
            #email = request.form['email']
            # user情報を確認
            #the_user = User.query.filter(User.email==email).all()
            the_user = User.query.filter(User.name==name).all()
            print(the_user)
            if len(the_user) == 0:
                # 存在しないなら登録処理
                #user = User(name=name, email=email)
                user = User(name=name)
                db.session.add(user)
                db.session.commit()
            else:
                # 存在するならOK（emailはユニークなので）
                name = the_user[0].name

            # セッション変数の設定
            session['user_name'] = name
            return redirect(url_for('index'))
        else:
            return
                    <form method="post">
                        <p><input type=text name=user_name required>
                        <!--<p><input type=text name=email required>-->
                        <p><input type=submit value=login>
                    </form>

    """

    # 認証画面を返す
    @app.route("/user/login", methods=["GET"])
    def get_twitter_request_token():
        try:
            # リクエストトークンを取得し, 認証urlを取得してリダイレクトする. 失敗したらトップページへのリンクを提示する.
            oauth_callback = "http://127.0.0.1:3000/callback"
            twitter = OAuth1Session(consumer_api_key, consumer_secret_key)
            twitter.fetch_request_token(request_token_url)
            auth_url = twitter.authorization_url(authorization_url)
            return redirect(auth_url)

        except Exception as e:
            print(e)
            # return '''login failed. <a href="http://localhost:3000>top</a>'''
            return f"{e}"

    @app.route("/user/callback", methods=["GET"])
    def callback():
        users_show_url = "https://api.twitter.com/1.1/users/show.json"
        try:
            # getパラメータを取得
            oauth_token = request.args.get("oauth_token")
            oauth_verifier = request.args.get("oauth_verifier")
            # リクエストトークン取得から返ってきたgetパラメータを用いてアクセストークンを取得. 失敗したら認証のときと同様
            twitter = OAuth1Session(
                consumer_api_key, consumer_secret_key, oauth_token, oauth_verifier
            )
            response = twitter.post(
                access_token_url, params={"oauth_verifier": oauth_verifier}
            )
            access_token = dict(parse_qsl(response.content.decode("utf-8")))

            twitter = OAuth1Session(
                consumer_api_key,
                consumer_secret_key,
                access_token["oauth_token"],
                access_token["oauth_token_secret"],
            )
            response = twitter.get(
                users_show_url, params={"user_id": access_token["user_id"]}
            )

            if response.status_code == 200:
                user_data = json.loads(response.text)
                # ユーザー登録とセッション情報の兼ね合いがどうなるか未定なのでこのようにしておく
                users = User.query.filter(
                    User.name == access_token["screen_name"]
                ).all()
                # users = User.query.filter(User.user_id==access_token['user_id']).all()

                # セッションID生成
                # session_id = str(uuid.uuid4())
                session_id = hashlib.sha256(
                    access_token["oauth_token"].encode("utf-8")
                ).hexdigest()
                if len(users) == 0:
                    # 存在しないなら登録処理
                    # user = User(name=user_data['screen_name'], user_id=access_token['user_id'])
                    user = User(name=user_data["screen_name"], session_id=session_id)
                    db.session.add(user)
                    db.session.commit()
                else:
                    # print(f"hello, {users[0].name}")
                    # user = User.query.filter(User.name==access_token['screen_name']).first()
                    user = users[0]
                    print(f"hello, {user.name}")
                    user.session_id = session_id
                    db.session.commit()
                db.session.close()

                # セッション変数の設定
                session["session_id"] = session_id
                session["user_name"] = access_token["screen_name"]
                session["user_id"] = access_token["user_id"]
                # session['oauth_token'] = access_token['oauth_token']
                # session['oauth_token_secret'] = access_token['oauth_token_secret']

                # アイコン画像URLから_normalを取り除きオリジナルサイズのものを得ている. https://syncer.jp/Web/API/Twitter/Snippet/4/
                image_url = re.sub(r"_normal", "", user_data["profile_image_url_https"])
                # 返すデータを整えてjsonでreturn
                response_data = {
                    "sessionId": session["session_id"],
                    "username": session["user_name"],
                    "profile_image_url": image_url,
                }
                # print(session)
                return jsonify(response_data)
            else:
                raise Exception(
                    f"response status code is not 200 (is {response.status_code})"
                )
        except Exception as e:
            print(e)
            # return '''login failed. <a href="http://localhost:3000>top</a>'''
            return f"{e}"

    @app.route("/user/logout", methods=["GET"])
    def logout():
        session_id = request.args.get("sessionID")
        # セッション変数の削除（この辺今は働いてないので必要ない）
        session.pop("session_id", None)
        session.pop("user_name", None)
        session.pop("user_id", None)
        user = User.query.filter(User.session_id == session_id).first()
        if user is not None:
            user.session_id = None
            db.session.commit()
        # session.pop('oauth_token', None)
        # session.pop('oauth_secret', None)
        # return redirect(url_for('login_test'))
        return redirect("http://127.0.0.1:3000")

    @app.route("/user/user_delete")
    def logout_and_delete():
        # データベースからユーザー情報を削除
        User.query.filter(User.name == access_token["screen_name"]).delete()
        db.session.commit()
        db.session.close()
        # セッション変数の削除
        session.pop("session_id", None)
        session.pop("user_name", None)
        session.pop("user_id", None)
        user = User.query.filter(User.session_id == session_id).first()
        if user is not None:
            user.session_id = None
            db.session.commit()
        # session.pop('oauth_token', None)
        # session.pop('oauth_secret', None)
        return "logout successed and user data deleted"

    @app.route("/user/recent", methods=["GET"])
    def fetch_recent_user_data():
        image_num = request.args.get("num")
        session_id = request.args.get("sessionID")
        user = User.query.filter(User.session_id == session_id).first()
        image_num = "4"
        user = User.query.filter(User.name == "Kw_I_KU").first()
        if user is not None:
            # todo : usersテーブルに直近の結果を持たせ、そこからとってくる.
            # likeunlikeの日付データを見て一番新しいやつを持ってくれば良い.
            joined_data = (
                db.session.query(LikeUnlike, AnimeData)
                .join(LikeUnlike, AnimeData.anime_id == LikeUnlike.anime_id)
                .filter(LikeUnlike.user_id == user.user_id)
                .order_by(desc(LikeUnlike.updated_at))
                .limit(int(image_num))
                .all()
            )
            response_data = {
                "anime" + str(i): img_encode(data[1].image)
                for i, data in enumerate(joined_data)
            }
            print([data[1].image for data in joined_data])
            return jsonify(response_data)
            pass
        else:
            return redirect(url_for("get_twitter_request_token"))

    # 指定した数(num)だけカードに表示するアニメの情報を取ってくる。DBにアクセスし、過去に表示したカード以外から適当に選んでくる。
    @app.route("/app/recs", methods=["GET"])
    def fetch_random_anime_data():
        image_num = request.args.get("num")
        session_id = request.args.get("sessionID")
        # テストするときはパラメータが無いので他で適当にfilter
        # user = User.query.filter(User.session_id==session_id).first()
        image_num = "4"
        user = User.query.filter(User.name == "Kw_I_KU").first()
        if user is not None:
            # todo usersテーブルに, 過去に表示したことのあるものをため込むカラムを作る. そこに入っていないものからランダムに選択する.
            # likeunlikeを参照すればいいのでは？
            lu_data = (
                db.session.query(LikeUnlike)
                .filter(LikeUnlike.user_id == user.user_id)
                .all()
            )
            past_animes = [lu.anime_id for lu in lu_data]
            # 過去に表示したことがあるものを含まないものからimage_num個に制限してとってくる
            animes = (
                db.session.query(AnimeData)
                .filter(AnimeData.anime_id.notin_(past_animes))
                .limit(int(image_num))
                .all()
            )
            response_data = {
                "anime"
                + str(i): {
                    "id": anime.anime_id,
                    "title": anime.title,
                    #'image': anime.image, # 画像をbase64で返す仕様についてはあとで
                    "image": img_encode(anime.image),
                    "description": anime.description,
                    "year": anime.year,
                    "genre": anime.genre,
                    "company": anime.company,
                }
                for i, anime in enumerate(animes)
            }
            return jsonify(response_data)
        else:
            return redirect("http://127.0.0.1:3000")

    @app.route("/test")
    def user_anime_matrix():
        # todo: user_idとanime_idを縦横にもち値がstatusの二次元配列を返す
        all_users = User.query.all()
        user_num = len(all_users)
        anime_num = len(AnimeData.query.all())
        user_id_list = [user.user_id for user in all_users]
        print("user_id_list:", user_id_list)
        res = []
        for user_id in user_id_list:
            # ユーザーひとりに対してアニメに対するlikeunlikeのstatusを取得, リストで保持する.
            """
            lu_data = db.session.query(LikeUnlike,AnimeData).\
                        join(LikeUnlike, AnimeData.anime_id==LikeUnlike.anime_id).\
                        filter(LikeUnlike.user_id==user_id).order_by(asc(LikeUnlike.anime_id)).all()
            """
            lu_data = (
                db.session.query(LikeUnlike)
                .filter(LikeUnlike.user_id == user_id)
                .order_by(asc(LikeUnlike.anime_id))
                .all()
            )
            # print(lu_data)

            if lu_data is not None:
                # そのユーザーがlike_unlikeを一つでも設定しているなら
                user_status_list = []
                index = 1  # user_status_listの要素数は最終的にanime_numにならないといけないのでそのようにする
                for data in lu_data:
                    data_anime_id = data.anime_id
                    data_status = data.status
                    # 前のループの次の場所からこのループのanime_idの場所まで0で埋める（デフォルト値）
                    user_status_list.extend([0] * (data_anime_id - index))
                    # このループのデータをいれる
                    user_status_list.append(data_status)
                    # インデックスを更新する
                    index = data_anime_id + 1
                # 終わったら最後までを0で埋める.
                user_status_list.extend([0] * (anime_num + 1 - index))
            else:
                # 一つもlike_unlikeをしていないなら全て0で埋める
                user_status_list = [0] * anime_num
            res.append(user_status_list)
        # return jsonify(res) # 確認用
        # アニメID順にステータスが並んだリストがユーザーごとに並んでいる二次元リストを返す.
        return res

    def anime_similarity():
        content_lu = np.array(user_anime_matrix()).T
        # anime_num, user_num = content_lu.shape[0], content_lu.shape[1]
        corr_mat = np.dot(content_lu, content_lu.T)
        anime_norm_mat = np.outer(np.linalg.norm(content_lu, axis=1))
        anime_norm_mat = np.where(
            np.absolute(anime_norm_mat) < 0.001, anime_norm_mat, 1
        )
        cos_sim_mat = corr_mat / anime_norm_mat
        cos_sim_mat = cos_sim_mat - np.diag(cos_sim_mat, k=0)
        return cos_sim_mat

    def collaborative_filtering(ith_anime: int) -> int:
        """
        i 番目のアニメに対して、コサイン類似度ベースの協調フィルタリングでレコメンドされたアニメのid を返します。
        """
        cos_sim_mat = anime_similarity()
        ret = np.argmax(cos_sim_mat[ith_anime])
        return ret

    """
    @app.route('/test')
    def testfunc():
        anime = AnimeData.query.filter(AnimeData.year.like('%2019%')).all()
        response_data = {'anime'+str(i):{'title': a.title, 'desc': a.description} for i,a in enumerate(anime)}
        #print(session)
        return jsonify(response_data)

    @app.route('/test2')
    def testfunc2():
        lu_data = db.session.query(AnimeData,LikeUnlike).\
                    join(LikeUnlike, AnimeData.anime_id==LikeUnlike.anime_id).\
                    filter(LikeUnlike.user_id==1).all()
        print(lu_data)
        return 'test2'
        response_data = {'anime'+str(i):{'user': lu.title, 'desc': lu.description} for i,lu in enumerate(lu_data)}
        #print(session)
        return jsonify(response_data)
    """

    return app


app = create_app()
