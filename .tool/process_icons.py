import json
import os
import sys
import xml.etree.ElementTree as ET
from xml.dom import minidom

# ================= 配置区域 =================
APPFILTER_XML_PATH = '../app/assets/appfilter.xml'  # 目标 appfilter.xml 路径
SVGS_DIR = '../svgs'                                # SVG 输出目录
INPUT_JSON_FILE = 'ai_output.json'               # AI 输出的 JSON 文件名
# ===========================================

def ensure_dir(directory):
    """确保目录存在"""
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"创建目录: {directory}")

def sanitize_resource_name(name):
    """
    清理并规范化资源名称，确保符合 Android 命名规范
    - 必须以字母开头
    - 只能包含字母、数字和下划线
    """
    # 替换非法字符为下划线
    safe_name = "".join([c if c.isalnum() or c == '_' else '_' for c in name])
    
    # 如果以数字开头，添加前缀 'a'
    if safe_name and safe_name[0].isdigit():
        safe_name = 'a' + safe_name
    
    # 确保不为空
    if not safe_name:
        safe_name = 'unnamed'
    
    return safe_name

def load_json_from_file(file_path):
    """从文件加载 JSON"""
    if not os.path.exists(file_path):
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            data = json.loads(content)
            if isinstance(data, list):
                return data
            else:
                print("错误: JSON 根节点不是数组")
                return []
    except json.JSONDecodeError as e:
        print(f"JSON 解析错误: {e}")
        return []
    except Exception as e:
        print(f"读取文件失败: {e}")
        return []

def save_svg(svg_content, file_name, directory):
    """保存 SVG 文件"""
    # 使用规范化函数处理文件名
    safe_name = sanitize_resource_name(file_name)
    full_path = os.path.join(directory, f"{safe_name}.svg")
    
    try:
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(svg_content)
        print(f"✅ 已保存 SVG: {full_path}")
        return safe_name
    except Exception as e:
        print(f"❌ 保存 SVG 失败 {file_name}: {e}")
        return None

def update_appfilter_xml(new_items_data, target_xml_path):
    """
    更新 appfilter.xml
    """
    if not os.path.exists(target_xml_path):
        print(f"❌ 错误: 目标文件不存在 {target_xml_path}")
        print("请确保 app/assets/appfilter.xml 路径正确")
        return

    try:
        tree = ET.parse(target_xml_path)
        root_target = tree.getroot()
    except ET.ParseError as e:
        print(f"❌ 解析 appfilter.xml 失败: {e}")
        return

    added_count = 0
    skipped_count = 0

    for ai_data in new_items_data:
        app_name = ai_data.get('app_name')
        component_info = ai_data.get('component')
        file_name = ai_data.get('file_name')
        
        if not all([app_name, component_info, file_name]):
            print(f"⚠️ 警告: 数据不完整，跳过: {ai_data.get('app_name', 'Unknown')}")
            continue
            
        # 检查是否已存在相同的 component (避免重复添加)
        exists = False
        for existing_item in root_target.findall('item'):
            if existing_item.get('component') == component_info:
                exists = True
                break
        
        if exists:
            print(f"⏭️ 跳过: {app_name} 已存在于 appfilter.xml 中")
            skipped_count += 1
            continue

        # 创建新的 item 元素
        new_item = ET.SubElement(root_target, 'item')
        new_item.set('component', component_info)
        new_item.set('drawable', file_name)
        new_item.set('name', app_name)
        
        added_count += 1
        print(f"➕ 准备添加: {app_name} -> {file_name}")

    if added_count > 0:
        # 格式化输出 XML
        rough_string = ET.tostring(root_target, encoding='unicode', xml_declaration=True)
        
        # 使用 minidom 进行美化
        dom = minidom.parseString(rough_string.encode('utf-8'))
        pretty_xml = dom.toprettyxml(indent="  ", encoding="UTF-8").decode('utf-8')
        
        # 移除 minidom 产生的多余空行和 XML 声明后的空行
        lines = [line for line in pretty_xml.split('\n') if line.strip()]
        
        # 重新构建 XML 字符串，保留 UTF-8 声明
        final_xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + '\n'.join(lines[1:]) if lines else ''

        try:
            with open(target_xml_path, 'w', encoding='utf-8') as f:
                f.write(final_xml)
            print(f"\n🎉 成功更新 {target_xml_path}，共添加 {added_count} 个条目，跳过 {skipped_count} 个已存在条目。")
        except Exception as e:
            print(f"❌ 写入文件失败: {e}")
    else:
        print("\n没有任何新条目需要添加。")

def main():
    print("="*30)
    print("Lawnicons 图标处理工具")
    print("="*30)
    
    ensure_dir(SVGS_DIR)
    
    # 1. 尝试从文件加载
    print(f"\n正在查找文件: {INPUT_JSON_FILE}...")
    ai_results = load_json_from_file(INPUT_JSON_FILE)
    
    if ai_results is None:
        print(f"文件 {INPUT_JSON_FILE} 不存在。")
        print("请将 AI 输出的 JSON 内容保存到该文件中，然后再次运行脚本。")
        return
    elif not ai_results:
        print("文件中没有有效的数据。")
        return

    print(f"✅ 成功加载 {len(ai_results)} 个应用数据。")

    # 2. 保存 SVG 文件
    print("\n正在保存 SVG 文件...")
    valid_results = []
    for data in ai_results:
        svg_content = data.get('svg_content')
        file_name = data.get('file_name')
        if svg_content and file_name:
            saved_name = save_svg(svg_content, file_name, SVGS_DIR)
            if saved_name:
                # 更新 file_name 为实际保存的名称（以防清理过）
                data['file_name'] = saved_name
                valid_results.append(data)
        else:
            print(f"⚠️ 跳过无效数据: {data.get('app_name')}")

    # 3. 更新 appfilter.xml
    print("\n正在更新 appfilter.xml...")
    if valid_results:
        update_appfilter_xml(valid_results, APPFILTER_XML_PATH)
    else:
        print("没有有效的 SVG 数据可处理。")

if __name__ == '__main__':
    main()
# python3 process_icons.py