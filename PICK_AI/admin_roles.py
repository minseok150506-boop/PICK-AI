from __future__ import annotations

import os
from werkzeug.security import generate_password_hash

from database import connect, now
from config import ADMIN_USERNAME


VALID_ROLES = {"owner", "admin", "subadmin", "user"}


def _role(row):
    if not row:
        return "user"
    value = str(row["role"] or "user").strip().lower()
    return value if value in VALID_ROLES else "user"


def get_user_role(user_id):
    if not user_id:
        return "user"
    conn = connect()
    row = conn.execute(
        "SELECT id,username,role FROM users WHERE id=?",
        (int(user_id),),
    ).fetchone()
    conn.close()
    if row and row["username"] == ADMIN_USERNAME:
        return "owner"
    return _role(row)


def is_admin(user_id):
    return get_user_role(user_id) in {"owner", "admin", "subadmin"}


def is_owner(user_id):
    return get_user_role(user_id) == "owner"


def is_subadmin(user_id):
    return get_user_role(user_id) == "subadmin"


def can_manage_roles(user_id):
    return get_user_role(user_id) in {"owner", "admin"}


def admin_label(user_id):
    return {
        "owner": "최고 관리자",
        "admin": "관리자",
        "subadmin": "부관리자",
        "user": "사용자",
    }.get(get_user_role(user_id), "사용자")


def list_users_for_admin(actor_id):
    if not is_admin(actor_id):
        raise PermissionError("관리자만 사용자 정보를 볼 수 있습니다.")

    actor_role = get_user_role(actor_id)
    actor_can_manage = can_manage_roles(actor_id)

    conn = connect()
    rows = conn.execute(
        "SELECT u.id,u.username,u.created_at,u.role,u.admin_granted_by,"
        " g.username AS granted_by_username"
        " FROM users u"
        " LEFT JOIN users g ON g.id=u.admin_granted_by"
        " ORDER BY datetime(u.created_at) ASC,u.id ASC"
    ).fetchall()

    result = []
    for row in rows:
        role = "owner" if row["username"] == ADMIN_USERNAME else _role(row)
        can_promote = bool(
            actor_can_manage
            and row["id"] != actor_id
            and role == "user"
        )

        can_demote = False
        if actor_can_manage and row["id"] != actor_id:
            if role == "admin":
                can_demote = (
                    actor_role == "owner"
                    or row["admin_granted_by"] == actor_id
                )
            elif role == "subadmin":
                can_demote = actor_role == "owner"

        result.append({
            "id": row["id"],
            "username": row["username"],
            "created_at": row["created_at"],
            "role": role,
            "display_role": {
                "owner": "최고 관리자",
                "admin": "관리자",
                "subadmin": "부관리자",
                "user": "사용자",
            }.get(role, "사용자"),
            "admin_granted_by": row["admin_granted_by"],
            "granted_by_username": row["granted_by_username"],
            "is_self": row["id"] == actor_id,
            "can_promote": can_promote,
            "can_demote": can_demote,
        })

    conn.close()
    return result


def promote_admin(actor_id, target_id):
    if not can_manage_roles(actor_id):
        raise PermissionError("부관리자는 관리자 권한을 부여할 수 없습니다.")
    if int(actor_id) == int(target_id):
        raise ValueError("자기 자신의 관리자 권한은 변경할 수 없습니다.")

    conn = connect()
    target = conn.execute(
        "SELECT id,username,role FROM users WHERE id=?",
        (int(target_id),),
    ).fetchone()
    if not target:
        conn.close()
        raise LookupError("사용자를 찾을 수 없습니다.")

    role = "owner" if target["username"] == ADMIN_USERNAME else _role(target)
    if role == "owner":
        conn.close()
        raise ValueError("최고 관리자 권한은 변경할 수 없습니다.")
    if role in {"admin", "subadmin"}:
        conn.close()
        raise ValueError("이미 관리자 권한이 있는 계정입니다.")

    conn.execute(
        "UPDATE users SET role='admin',admin_granted_by=? WHERE id=?",
        (int(actor_id), int(target_id)),
    )
    conn.commit()
    conn.close()


def demote_admin(actor_id, target_id):
    if not can_manage_roles(actor_id):
        raise PermissionError("부관리자는 관리자 권한을 해제할 수 없습니다.")
    if int(actor_id) == int(target_id):
        raise ValueError("자기 자신의 관리자 권한은 해제할 수 없습니다.")

    actor_role = get_user_role(actor_id)
    conn = connect()
    target = conn.execute(
        "SELECT id,username,role,admin_granted_by FROM users WHERE id=?",
        (int(target_id),),
    ).fetchone()
    if not target:
        conn.close()
        raise LookupError("사용자를 찾을 수 없습니다.")

    role = "owner" if target["username"] == ADMIN_USERNAME else _role(target)
    if role == "owner":
        conn.close()
        raise ValueError("최고 관리자 권한은 해제할 수 없습니다.")

    if role == "subadmin":
        if actor_role != "owner":
            conn.close()
            raise PermissionError("부관리자 권한은 최고 관리자만 해제할 수 있습니다.")
        conn.execute(
            "UPDATE users SET role='user',admin_granted_by=NULL WHERE id=?",
            (int(target_id),),
        )
        conn.commit()
        conn.close()
        return

    if role != "admin":
        conn.close()
        raise ValueError("관리자가 아닌 사용자입니다.")

    if actor_role != "owner" and target["admin_granted_by"] != int(actor_id):
        conn.close()
        raise PermissionError("자신이 지정한 관리자만 해제할 수 있습니다.")

    conn.execute(
        "UPDATE users SET admin_granted_by=?"
        " WHERE role='admin' AND admin_granted_by=?",
        (int(actor_id), int(target_id)),
    )
    conn.execute(
        "UPDATE users SET role='user',admin_granted_by=NULL WHERE id=?",
        (int(target_id),),
    )
    conn.commit()
    conn.close()


def ensure_subadmin_account():
    username = str(
        os.environ.get("PICK_SUBADMIN_USERNAME") or "YE JUN CHO"
    ).strip()
    password = str(
        os.environ.get("PICK_SUBADMIN_PASSWORD") or ""
    ).strip()

    if not username:
        return {"ok": False, "configured": False, "reason": "username_missing"}

    conn = connect()
    row = conn.execute(
        "SELECT id,username,role FROM users WHERE username=?",
        (username,),
    ).fetchone()

    if row:
        if row["username"] == ADMIN_USERNAME:
            conn.close()
            return {
                "ok": False,
                "configured": True,
                "reason": "username_is_owner",
            }

        if password:
            conn.execute(
                "UPDATE users SET role='subadmin',password_hash=?,"
                "admin_granted_by=NULL WHERE id=?",
                (generate_password_hash(password), int(row["id"])),
            )
        else:
            conn.execute(
                "UPDATE users SET role='subadmin',admin_granted_by=NULL WHERE id=?",
                (int(row["id"]),),
            )
        conn.commit()
        user_id = int(row["id"])
        created = False
    else:
        if not password:
            conn.close()
            return {
                "ok": False,
                "configured": False,
                "reason": "password_missing",
            }

        cur = conn.execute(
            "INSERT INTO users(username,password_hash,created_at,role,admin_granted_by)"
            " VALUES(?,?,?,'subadmin',NULL)",
            (username, generate_password_hash(password), now()),
        )
        conn.commit()
        user_id = int(cur.lastrowid)
        created = True

    conn.close()
    return {
        "ok": True,
        "configured": True,
        "created": created,
        "user_id": user_id,
        "username": username,
        "role": "subadmin",
    }
