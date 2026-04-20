from flask import Blueprint, render_template, request, redirect, session, flash, url_for
from database import conectar
from functools import wraps

auth = Blueprint("auth", __name__)

# ─── DECORATORS DE PERMISSÃO ────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user"):
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user"):
            return redirect("/login")
        if session.get("nivel") != "admin":
            flash("Acesso restrito ao administrador.", "error")
            return redirect("/dashboard")
        return f(*args, **kwargs)
    return decorated

def aux_ou_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user"):
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated

# ─── LOGIN / LOGOUT ─────────────────────────────────────────────────────────

@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user  = request.form.get("user", "").strip()
        senha = request.form.get("senha", "").strip()

        if not user or not senha:
            flash("Preencha usuário e senha.", "error")
            return render_template("login.html")

        conn = conectar()
        c    = conn.cursor()
        c.execute("SELECT * FROM usuarios WHERE username=%s AND senha=%s", (user, senha))
        usuario = c.fetchone()
        conn.close()

        if usuario:
            session["user"]  = usuario["username"]
            session["nivel"] = usuario["tipo"]
            session["uid"]   = usuario["id"]
            return redirect("/dashboard")
        else:
            flash("Usuário ou senha incorretos.", "error")

    return render_template("login.html")


@auth.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ─── GESTÃO DE USUÁRIOS (só admin) ──────────────────────────────────────────

@auth.route("/usuarios")
@admin_required
def listar_usuarios():
    conn = conectar()
    c    = conn.cursor()
    c.execute("SELECT id, username, tipo FROM usuarios ORDER BY tipo, username")
    usuarios = c.fetchall()
    conn.close()
    return render_template("usuarios.html", usuarios=usuarios)


@auth.route("/usuarios/novo", methods=["GET", "POST"])
@admin_required
def novo_usuario():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        senha    = request.form.get("senha", "").strip()
        tipo     = request.form.get("tipo", "aux")

        if not username or not senha:
            flash("Preencha todos os campos.", "error")
            return render_template("usuario_form.html", usuario=None)

        conn = conectar()
        c    = conn.cursor()
        try:
            c.execute("INSERT INTO usuarios (username, senha, tipo) VALUES (%s, %s, %s)",
                      (username, senha, tipo))
            conn.commit()
            flash(f"Usuário '{username}' criado com sucesso!", "success")
        except Exception:
            conn.rollback()
            flash("Nome de usuário já existe.", "error")
        finally:
            conn.close()
        return redirect(url_for("auth.listar_usuarios"))

    return render_template("usuario_form.html", usuario=None)


@auth.route("/usuarios/editar/<int:uid>", methods=["GET", "POST"])
@admin_required
def editar_usuario(uid):
    conn = conectar()
    c    = conn.cursor()

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        senha    = request.form.get("senha", "").strip()
        tipo     = request.form.get("tipo", "aux")

        if senha:
            c.execute("UPDATE usuarios SET username=%s, senha=%s, tipo=%s WHERE id=%s",
                      (username, senha, tipo, uid))
        else:
            c.execute("UPDATE usuarios SET username=%s, tipo=%s WHERE id=%s",
                      (username, tipo, uid))
        conn.commit()
        conn.close()
        flash("Usuário atualizado.", "success")
        return redirect(url_for("auth.listar_usuarios"))

    c.execute("SELECT * FROM usuarios WHERE id=%s", (uid,))
    usuario = c.fetchone()
    conn.close()
    return render_template("usuario_form.html", usuario=usuario)


@auth.route("/usuarios/excluir/<int:uid>", methods=["POST"])
@admin_required
def excluir_usuario(uid):
    if uid == session.get("uid"):
        flash("Você não pode excluir seu próprio usuário.", "error")
        return redirect(url_for("auth.listar_usuarios"))
    conn = conectar()
    c    = conn.cursor()
    c.execute("DELETE FROM usuarios WHERE id=%s", (uid,))
    conn.commit()
    conn.close()
    flash("Usuário removido.", "success")
    return redirect(url_for("auth.listar_usuarios"))
