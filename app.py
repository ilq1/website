import os
from flask import Flask, render_template, redirect, url_for, session, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from authlib.integrations.flask_client import OAuth

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'super-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
oauth = OAuth(app)

# GitHub
github = oauth.register(
    name='github',
    client_id=os.environ.get('GITHUB_CLIENT_ID', 'DUMMY_GITHUB_ID'),
    client_secret=os.environ.get('GITHUB_CLIENT_SECRET', 'DUMMY_GITHUB_SECRET'),
    access_token_url='https://github.com/login/oauth/access_token',
    access_token_params=None,
    authorize_url='https://github.com/login/oauth/authorize',
    authorize_params=None,
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email'},
)

# VK
vk = oauth.register(
    name='vk',
    client_id=os.environ.get('VK_CLIENT_ID', 'DUMMY_VK_ID'),
    client_secret=os.environ.get('VK_CLIENT_SECRET', 'DUMMY_VK_SECRET'),
    access_token_url='https://oauth.vk.com/access_token',
    access_token_params=None,
    authorize_url='https://oauth.vk.com/authorize',
    authorize_params=None,
    api_base_url='https://api.vk.com/method/',
    client_kwargs={'scope': 'email'},
)

# Модель пользователя
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    provider = db.Column(db.String(50), nullable=False)
    provider_id = db.Column(db.String(100), unique=True, nullable=False)
    comments = db.relationship('Comment', backref='author', lazy=True)

# Модель проектов/курсовых
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    repo_url = db.Column(db.String(250), nullable=False)

# Модель комментариев
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

with app.app_context():
    db.create_all()
    if not Project.query.first():
        db.session.add(Project(
            name="Демонстрация работы STP/RSTP", 
            description="Улучшение функциональности miminet: команды link donw и sleep для коммутатора",
            repo_url="https://github.com/mimi-net/miminet/pull/383"
        ))
        db.session.add(Project(
            name="Сайт визитка", 
            description="Репозиторий веб-сайта",
            repo_url="https://github.com/ilq1/website"
        ))
        db.session.commit()

@app.route('/')
def index():
    projects = Project.query.all()
    comments = Comment.query.order_by(Comment.created_at.desc()).all()
    user = session.get('user')
    return render_template('index.html', projects=projects, comments=comments, user=user)

@app.route('/login/<provider_name>')
def login(provider_name):
    client = oauth.create_client(provider_name)
    if not client:
        return "Провайдер не найден", 404
    redirect_uri = url_for('authorize', provider_name=provider_name, _external=True)
    return client.authorize_redirect(redirect_uri)

@app.route('/authorize/<provider_name>')
def authorize(provider_name):
    client = oauth.create_client(provider_name)
    if not client:
        return "Провайдер не найден", 404
    
    token = client.authorize_access_token()
    
    if provider_name == 'github':
        resp = client.get('user')
        user_info = resp.json()
        provider_id = str(user_info.get('id'))
        username = user_info.get('login')
        email = user_info.get('email')
    elif provider_name == 'vk':

        email = token.get('email')
        user_id = token.get('user_id')
        access_token = token.get('access_token')
        
        
        resp = client.get('users.get', params={'access_token': access_token, 'v': '5.131'})
        data = resp.json()
        
        if 'response' in data and len(data['response']) > 0:
            user_data = data['response'][0]
            first = user_data.get('first_name', '')
            last = user_data.get('last_name', '')
            username = f"{first} {last}".strip()
        else:
            username = f"VK User {user_id}"
            
        provider_id = str(user_id)

    user = User.query.filter_by(provider=provider_name, provider_id=provider_id).first()
    if not user:
        user = User(username=username, email=email, provider=provider_name, provider_id=provider_id)
        db.session.add(user)
        db.session.commit()

    session['user'] = {'id': user.id, 'username': user.username}
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

@app.route('/comment', methods=['POST'])
def add_comment():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    content = request.form.get('content')
    if not content:
        return jsonify({'error': 'Comment is empty'}), 400

    user = User.query.get(session['user']['id'])
    comment = Comment(content=content, author=user)
    db.session.add(comment)
    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'id': comment.id,
            'content': comment.content,
            'author': {
                'username': user.username
            },
            'created_at': comment.created_at.strftime('%d.%m')
        })
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)