from __future__ import annotations

from database import connect
from config import ADMIN_USERNAME


def _role(row):
    if not row:
        return "user"
    value = str(row["role"] or "user").strip().lower()
    return value if value in {"owner", "admin", "user"} else "user"


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
    return get_user_role(user_id) in {"owner", "admin"}


def is_owner(user_id):
    return get_user_role(user_id) == "owner"


def admin_label(user_id):
    if not user_id:
        return "사용자"
    conn = connect()
    row = conn.execute(
        "SELECT id,username,role FROM users WHERE id=?",
        (int(user_id),),
    ).fetchone()
    if not row:
        conn.close()
        return "사용자"

    role = "owner" if row["username"] == ADMIN_USERNAME else _role(row)
    if role == "owner":
        conn.close()
        return "대표 관리자"

    if role == "admin":
        child = conn.execute(
            "SELECT 1 FROM users WHERE role='admin' AND admin_granted_by=? LIMIT 1",
            (int(user_id),),
        ).fetchone()
        conn.close()
        return "대표 관리자" if child else "관리자"

    conn.close()
    return "사용자"


def list_users_for_admin(actor_id):
    if not is_admin(actor_id):
        raise PermissionError("관리자만 사용자 정보를 볼 수 있습니다.")

    actor_role = get_user_role(actor_id)
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
        child = conn.execute(
            "SELECT 1 FROM users WHERE role='admin' AND admin_granted_by=? LIMIT 1",
            (row["id"],),
        ).fetchone()

        if role == "owner" or (role == "admin" and child):
            display_role = "대표 관리자"
        elif role == "admin":
            display_role = "관리자"
        else:
            display_role = "사용자"

        result.append({
            "id": row["id"],
            "username": row["username"],
            "created_at": row["created_at"],
            "role": role,
            "display_role": display_role,
            "admin_granted_by": row["admin_granted_by"],
            "granted_by_username": row["granted_by_username"],
            "is_self": row["id"] == actor_id,
            "can_promote": row["id"] != actor_id and role == "user",
            "can_demote": (
                row["id"] != actor_id
                and role == "admin"
                and (
                    actor_role == "owner"
                    or row["admin_granted_by"] == actor_id
                )
            ),
        })
    conn.close()
    return result


def promote_admin(actor_id, target_id):
    if not is_admin(actor_id):
        raise PermissionError("관리자만 다른 사용자를 관리자로 지정할 수 있습니다.")
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
        raise ValueError("대표 관리자 권한은 변경할 수 없습니다.")
    if role == "admin":
        conn.close()
        raise ValueError("이미 관리자입니다.")

    conn.execute(
        "UPDATE users SET role='admin',admin_granted_by=? WHERE id=?",
        (int(actor_id), int(target_id)),
    )
    conn.commit()
    conn.close()


def demote_admin(actor_id, target_id):
    if not is_admin(actor_id):
        raise PermissionError("관리자만 관리자 권한을 해제할 수 있습니다.")
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
        raise ValueError("대표 관리자 권한은 해제할 수 없습니다.")
    if role != "admin":
        conn.close()
        raise ValueError("관리자가 아닌 사용자입니다.")

    if actor_role != "owner" and target["admin_granted_by"] != int(actor_id):
        conn.close()
        raise PermissionError("자신이 지정한 관리자만 해제할 수 있습니다.")

    # If this admin created other admins, transfer them to the actor.
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
