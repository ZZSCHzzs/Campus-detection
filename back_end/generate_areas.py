#!/usr/bin/env python
"""
区域和节点批量生成脚本
用于快速创建区域模型和绑定的硬件节点
"""

import os
import sys
import django

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus_detection.settings')
django.setup()

from webapi.models import Building, Area, HardwareNode, ProcessTerminal


def create_default_terminal():
    """创建默认终端，如果不存在的话"""
    terminal, created = ProcessTerminal.objects.get_or_create(
        id=1,
        defaults={
            'name': '默认终端',
            'status': False,
            'mode': 'both',
            'interval': 5.0,
            'co2_enabled': True,
            'co2_read_interval': 30,
        }
    )
    if created:
        print(f"创建了默认终端：{terminal.name}")
    return terminal


def create_default_building():
    """创建默认建筑，如果不存在的话"""
    building, created = Building.objects.get_or_create(
        id=1,
        defaults={
            'name': '主楼',
            'description': '校园主教学楼'
        }
    )
    if created:
        print(f"创建了默认建筑：{building.name}")
    return building


def generate_areas_and_nodes(area_names=None, building_name="主楼", floor=1):
    """
    批量生成区域和对应的硬件节点
    
    Args:
        area_names: 区域名称列表，如果为None则使用默认列表
        building_name: 建筑名称
        floor: 楼层
    """
    if area_names is None:
        area_names = [
            "图书馆大厅", "阅览室A", "阅览室B", "自习室1", "自习室2",
            "教学楼大厅", "101教室", "102教室", "103教室", "201教室",
            "学生食堂", "教工食堂", "咖啡厅", "便利店", "活动中心",
            "体育馆", "健身房", "游泳池", "篮球场", "网球场"
        ]
    
    print(f"开始生成 {len(area_names)} 个区域和对应节点...")
    
    # 确保有默认的建筑和终端
    terminal = create_default_terminal()
    
    # 获取或创建建筑
    building, created = Building.objects.get_or_create(
        name=building_name,
        defaults={'description': f'{building_name} - 自动生成'}
    )
    if created:
        print(f"创建了建筑：{building.name}")
    
    created_areas = []
    created_nodes = []
    
    for i, area_name in enumerate(area_names, 1):
        # 检查区域是否已存在
        if Area.objects.filter(name=area_name).exists():
            print(f"区域 '{area_name}' 已存在，跳过")
            continue
        
        # 创建硬件节点
        node_name = f"node{i:03d}"  # node001, node002, ...
        node, node_created = HardwareNode.objects.get_or_create(
            name=node_name,
            defaults={
                'detected_count': 0,
                'terminal': terminal,
                'status': False,
                'description': f'区域 {area_name} 的检测节点',
                'temperature': 22.0 + (i % 5),  # 模拟不同的初始温度
                'humidity': 50.0 + (i % 20),    # 模拟不同的初始湿度
            }
        )
        
        if node_created:
            created_nodes.append(node)
            print(f"创建了硬件节点：{node.name}")
        
        # 创建区域并绑定节点
        area = Area.objects.create(
            name=area_name,
            bound_node=node,
            description=f'{area_name} - 自动生成',
            type=building,
            floor=floor,
            capacity=50 + (i % 100)  # 模拟不同的容量
        )
        created_areas.append(area)
        print(f"创建了区域：{area.name} -> 绑定节点：{node.name}")
    
    return created_areas, created_nodes


def list_existing_data():
    """列出现有的数据"""
    buildings = Building.objects.all()
    areas = Area.objects.all()
    nodes = HardwareNode.objects.all()
    terminals = ProcessTerminal.objects.all()
    
    print("\n当前系统数据：")
    print(f"建筑数量：{buildings.count()}")
    for building in buildings:
        print(f"  - {building.name} (ID: {building.id})")
    
    print(f"终端数量：{terminals.count()}")
    for terminal in terminals:
        print(f"  - {terminal.name} (ID: {terminal.id})")
    
    print(f"区域数量：{areas.count()}")
    for area in areas:
        print(f"  - {area.name} -> {area.bound_node.name} (楼层: {area.floor})")
    
    print(f"硬件节点数量：{nodes.count()}")
    for node in nodes:
        print(f"  - {node.name} (终端: {node.terminal.name})")


def clean_existing_data():
    """清理现有数据"""
    area_count = Area.objects.count()
    node_count = HardwareNode.objects.count()
    
    if area_count > 0 or node_count > 0:
        print(f"\n发现现有数据：{area_count} 个区域，{node_count} 个硬件节点")
        response = input("是否清理现有的区域和节点数据？(y/N): ")
        if response.lower() == 'y':
            # 删除区域（会级联删除相关数据）
            Area.objects.all().delete()
            # 删除硬件节点
            HardwareNode.objects.all().delete()
            print("已清理现有的区域和节点数据")
            return True
        else:
            print("保留现有数据")
            return False
    return True


def interactive_input():
    """交互式输入区域名称"""
    print("\n请输入区域名称（一行一个，输入空行结束）：")
    area_names = []
    while True:
        name = input(f"区域 {len(area_names) + 1}: ").strip()
        if not name:
            break
        area_names.append(name)
    
    return area_names


def main():
    """主函数"""
    print("=" * 50)
    print("校园检测系统 - 区域和节点生成脚本")
    print("=" * 50)
    
    # 显示现有数据
    list_existing_data()
    
    # 选择操作模式
    print("\n请选择操作模式：")
    print("1. 使用默认区域列表（20个常见校园区域）")
    print("2. 手动输入区域列表")
    print("3. 仅查看现有数据")
    print("4. 清理所有数据")
    
    choice = input("请选择 (1-4): ").strip()
    
    if choice == "3":
        print("操作完成")
        return
    elif choice == "4":
        if clean_existing_data():
            print("数据清理完成")
        return
    
    # 清理现有数据
    if not clean_existing_data():
        return
    
    # 获取区域名称列表
    if choice == "2":
        area_names = interactive_input()
        if not area_names:
            print("未输入任何区域名称，退出")
            return
    else:
        area_names = None  # 使用默认列表
    
    # 获取建筑信息
    building_name = input("\n请输入建筑名称 (默认: 主楼): ").strip() or "主楼"
    try:
        floor = int(input("请输入楼层 (默认: 1): ").strip() or "1")
    except ValueError:
        floor = 1
        print("楼层输入无效，使用默认值：1")
    
    print(f"\n将在建筑 '{building_name}' 的第 {floor} 层创建区域和节点")
    
    # 确认生成
    if area_names:
        print(f"将创建 {len(area_names)} 个区域：")
        for i, name in enumerate(area_names, 1):
            print(f"  {i}. {name}")
    else:
        print("将创建 20 个默认校园区域")
    
    confirm = input("\n确认开始生成？(y/N): ")
    if confirm.lower() != 'y':
        print("已取消生成")
        return
    
    try:
        # 生成区域和节点
        created_areas, created_nodes = generate_areas_and_nodes(
            area_names=area_names,
            building_name=building_name,
            floor=floor
        )
        
        print(f"\n" + "=" * 50)
        print("生成完成！")
        print(f"成功创建了 {len(created_areas)} 个区域")
        print(f"成功创建了 {len(created_nodes)} 个硬件节点")
        print("=" * 50)
        
        # 显示最终结果
        print("\n最终数据统计：")
        list_existing_data()
        
    except Exception as e:
        print(f"生成过程中出错：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 