# permissions.py
from rest_framework import permissions


class StaffEditSelected(permissions.BasePermission):
    """
    Staff 只能编辑标记为 allow_staff_edit 的资源
    Admin 拥有全部权限
    """

    def has_permission(self, request, view):
        # 未认证用户只读
        if not request.user.is_authenticated:
            return request.method in permissions.SAFE_METHODS

        # Admin 拥有全部权限
        if request.user.is_superuser:
            return True

        # Staff 检查视图是否允许编辑
        if request.user.is_staff:
            return getattr(view, 'allow_staff_edit', False) or request.method in permissions.SAFE_METHODS

        # 普通认证用户只读
        return request.method in permissions.SAFE_METHODS

    def has_object_permission(self, request, view, obj):
        # 对象级权限控制（可选）
        return self.has_permission(request, view)