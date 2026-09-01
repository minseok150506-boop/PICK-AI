from __future__ import annotations

from database import connect
from config import ADMIN_USERNAME


VALID_ROLES = {"owner", "admin", "user"}


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
    return get_user_role(user_id) in {"owner", "admin"}


def is_owner(user_id):
    return get_user_role(user_id) == "owner"


def can_manage_roles(user_id):
    return is_owner(user_id)


def admin_label(user_id):
    return {
        "owner": "최고 관리자",
        "admin": "관리자",
        "user": "사용자",
    }.get(get_user_role(user_id), "사용자")


def normalize_legacy_admin_roles():
    """Old subadmin accounts become normal users; account data is preserved."""
    conn = connect()
    cur = conn.execute(
        "UPDATE users SET role='user',admin_granted_by=NULL WHERE role='subadmin'"
    )
    conn.commit()
    changed = max(0, int(getattr(cur, "rowcount", 0) or 0))
    conn.close()
    return changed


def list_users_for_admin(actor_id):
    if not is_admin(actor_id):
        raise PermissionError("관리자만 사용자 정보를 볼 수 있습니다.")

    owner = is_owner(actor_id)
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
        is_self = int(row["id"]) == int(actor_id)
        result.append({
            "id": row["id"],
            "username": row["username"],
            "created_at": row["created_at"],
            "role": role,
            "display_role": {
                "owner": "최고 관리자",
                "admin": "관리자",
                "user": "사용자",
            }.get(role, "사용자"),
            "admin_granted_by": row["admin_granted_by"],
            "granted_by_username": row["granted_by_username"],
            "is_self": is_self,
            "can_promote": bool(owner and not is_self and role == "user"),
            "can_demote": bool(owner and not is_self and role == "admin"),
        })

    conn.close()
    return result


def promote_admin(actor_id, target_id):
    if not is_owner(actor_id):
        raise PermissionError("최고 관리자만 관리자 권한을 지정할 수 있습니다.")
    if int(actor_id) == int(target_id):
        raise ValueError("자기 자신의 권한은 변경할 수 없습니다.")

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
    if not is_owner(actor_id):
        raise PermissionError("최고 관리자만 관리자 권한을 해제할 수 있습니다.")
    if int(actor_id) == int(target_id):
        raise ValueError("자기 자신의 관리자 권한은 해제할 수 없습니다.")

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
        raise ValueError("최고 관리자 권한은 해제할 수 없습니다.")
    if role != "admin":
        conn.close()
        raise ValueError("관리자가 아닌 사용자입니다.")

    conn.execute(
        "UPDATE users SET role='user',admin_granted_by=NULL WHERE id=?",
        (int(target_id),),
    )
    conn.commit()
    conn.close()
