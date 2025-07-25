#!/usr/bin/env python
"""
优化的楼宇和区域批量生成脚本
支持解析教务系统JSON格式数据
"""

import os
import sys
import django
import json
import re

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus_detection.settings')
django.setup()

from webapi.models import Building, Area, HardwareNode


def parse_floor_from_area_name(area_name):
    """
    从区域名称解析楼层信息
    例如："8号楼332" -> 3, "主楼101" -> 1, "格物楼B201" -> 2
    """
    # 查找末尾的数字串
    match = re.search(r'(\d+)$', area_name)
    if match:
        number_str = match.group(1)
        if len(number_str) >= 3:  # 如果是3位或以上数字，取第一位作为楼层
            return int(number_str[0])
        elif len(number_str) >= 1:  # 如果是1-2位数字，直接作为楼层
            return int(number_str)
    
    # 如果没有找到数字，默认返回1层
    return 1


def create_buildings_from_json(json_data):
    """
    从教务系统JSON数据创建建筑模型
    
    Args:
        json_data: 教务系统的JSON数据，包含MC(名称)、DM(代码)、KYF等字段
    
    Returns:
        list: 创建的建筑对象列表
    """
    print("开始解析教务系统JSON数据...")
    
    try:
        if isinstance(json_data, str):
            buildings_data = json.loads(json_data)
        else:
            buildings_data = json_data
    except json.JSONDecodeError as e:
        print(f"JSON解析错误：{e}")
        return []
    
    created_buildings = []
    
    for building_data in buildings_data:
        building_name = building_data.get('MC', '未知建筑')
        building_code = building_data.get('DM', '')
        
        # 检查建筑是否已存在
        building, created = Building.objects.get_or_create(
            name=building_name,
            defaults={
                'description': f'教务系统导入 - 代码：{building_code}'
            }
        )
        
        if created:
            print(f"✓ 创建建筑：{building_name} (代码：{building_code})")
            created_buildings.append(building)
        else:
            print(f"- 建筑已存在：{building_name}")
            created_buildings.append(building)
    
    return created_buildings


def create_areas_for_building(building, areas_json_data, target_node_id=12):
    """
    为指定建筑创建区域
    
    Args:
        building: 建筑对象
        areas_json_data: 区域JSON数据，包含MC(名称)、DM(代码)等字段
        target_node_id: 目标节点ID，默认为12
    
    Returns:
        list: 创建的区域对象列表
    """
    print(f"\n为建筑 '{building.name}' 创建区域...")
    
    # 获取目标节点
    try:
        target_node = HardwareNode.objects.get(id=target_node_id)
        print(f"使用节点：{target_node.name} (ID: {target_node_id})")
    except HardwareNode.DoesNotExist:
        print(f"错误：找不到ID为{target_node_id}的节点")
        return []
    
    try:
        if isinstance(areas_json_data, str):
            areas_data = json.loads(areas_json_data)
        else:
            areas_data = areas_json_data
    except json.JSONDecodeError as e:
        print(f"区域JSON解析错误：{e}")
        return []
    
    created_areas = []
    
    for area_data in areas_data:
        area_name = area_data.get('MC', '未知区域')
        area_code = area_data.get('DM', '')
        
        # 解析楼层
        floor = parse_floor_from_area_name(area_name)
        
        # 检查区域是否已存在
        if Area.objects.filter(name=area_name, type=building).exists():
            print(f"- 区域已存在：{area_name}")
            continue
        
        # 创建区域
        area = Area.objects.create(
            name=area_name,
            bound_node=target_node,
            description=f'教务系统导入 - 代码：{area_code}',
            type=building,
            floor=floor,
            capacity=50  # 默认容量
        )
        
        created_areas.append(area)
        print(f"✓ 创建区域：{area_name} -> 楼层：{floor} -> 节点：{target_node.name}")
    
    return created_areas


def interactive_area_input():
    """
    交互式区域数据输入
    
    Returns:
        str: 用户输入的JSON字符串
    """
    print("\n请粘贴区域JSON数据（格式如：[{\"MC\": \"8号楼332\", \"DM\": \"10141\"}, ...]）：")
    print("输入完成后按回车，然后输入 'END' 并按回车结束输入")
    
    lines = []
    while True:
        line = input()
        if line.strip() == 'END':
            break
        lines.append(line)
    
    return '\n'.join(lines)


def main():
    """
    主函数
    """
    print("=" * 60)
    print("校园检测系统 - 优化的楼宇和区域生成脚本")
    print("=" * 60)
    
    # 步骤1：输入楼宇JSON数据
    print("\n步骤1：请粘贴教务系统的楼宇JSON数据")
    print("格式示例：[{\"MC\": \"8号楼\", \"DM\": \"001\", \"KYF\": \"1\"}, ...]")
    print("输入完成后按回车，然后输入 'END' 并按回车结束输入")
    
    # 读取楼宇JSON数据
    buildings_json_lines = []
    while True:
        line = input()
        if line.strip() == 'END':
            break
        buildings_json_lines.append(line)
    
    buildings_json_str = '\n'.join(buildings_json_lines)
    
    if not buildings_json_str.strip():
        print("未输入楼宇数据，退出")
        return
    
    # 解析并创建建筑
    buildings = create_buildings_from_json(buildings_json_str)
    
    if not buildings:
        print("没有成功创建任何建筑，退出")
        return
    
    print(f"\n成功处理 {len(buildings)} 个建筑")
    
    # 检查目标节点是否存在
    target_node_id = 12
    try:
        target_node = HardwareNode.objects.get(id=target_node_id)
        print(f"\n目标节点确认：{target_node.name} (ID: {target_node_id})")
    except HardwareNode.DoesNotExist:
        print(f"\n错误：找不到ID为{target_node_id}的节点")
        print("请确保该节点存在后再运行脚本")
        return
    
    # 步骤2：为每个建筑输入区域数据
    print("\n" + "=" * 60)
    print("步骤2：为每个建筑输入区域数据")
    print("=" * 60)
    
    total_created_areas = 0
    
    for i, building in enumerate(buildings, 1):
        print(f"\n[{i}/{len(buildings)}] 当前建筑：{building.name}")
        
        # 询问是否为此建筑添加区域
        choice = input(f"是否为 '{building.name}' 添加区域？(y/n/skip): ").strip().lower()
        
        if choice == 'n':
            print("跳过此建筑")
            continue
        elif choice == 'skip':
            print("跳过此建筑")
            continue
        elif choice != 'y':
            print("输入无效，跳过此建筑")
            continue
        
        # 输入区域数据
        areas_json_str = interactive_area_input()
        
        if not areas_json_str.strip():
            print("未输入区域数据，跳过此建筑")
            continue
        
        # 创建区域
        created_areas = create_areas_for_building(building, areas_json_str, target_node_id)
        total_created_areas += len(created_areas)
        
        print(f"为建筑 '{building.name}' 成功创建 {len(created_areas)} 个区域")
    
    # 总结
    print("\n" + "=" * 60)
    print("生成完成！")
    print(f"总计创建：{len(buildings)} 个建筑，{total_created_areas} 个区域")
    print(f"所有区域均绑定到节点：{target_node.name} (ID: {target_node_id})")
    print("=" * 60)
    
    # 显示最终统计
    print("\n最终数据统计：")
    print(f"建筑总数：{Building.objects.count()}")
    print(f"区域总数：{Area.objects.count()}")
    print(f"硬件节点总数：{HardwareNode.objects.count()}")


if __name__ == "__main__":
    main()