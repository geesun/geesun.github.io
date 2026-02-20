#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据main_parsed.json的层级结构，获取每个href对应的CSV文件
目录结构和层次结构与JSON一致
"""

import json
import os
import re
import csv
import time
from urllib.request import urlopen, Request
from urllib.parse import quote
from urllib.error import URLError, HTTPError

# Cookie（从浏览器开发者工具获取）
COOKIE = '.SpiderForum=39C3812FF342DDC067C65954D8248E8ED4C6254F5D172DC6BFD5ABB9BE0A06E959273DDFA1ECF55FA0F89C64165A0EDD5EAA7837219A676B5D1F7904C859328064345142A72DCDA78CAF9C17EBD1E720C8B321981C37A4C0334368B26F9FB94AE83E2E87BE293750A6B25051FA31A563FF2487D7909BA3346B0C6FDEFC90B7115947B07A77E27129ED522F3F9F5A618CE42A44E7023E01E196759020DB1277C11E56A7DD; Languages=; MemberId=7e9ae397-b609-45bb-a7cd-4a05f5f69b0c; UserEntityId=15276; UserName=%e5%8d%97%e6%98%8c%e8%b0%b1%e6%ba%90%e5%85%ac%e5%8f%b8; ASP.NET_SessionId=sdk1wdjpk4oxt345esezp1vl'

# 基础输出目录
BASE_DIR = 'parsed_genealogy'

def fetch_html(url):
    """从URL获取HTML内容"""
    try:
        # 分离URL的基础部分和参数部分
        if '?' in url:
            base_url, params = url.split('?', 1)
            # 编码参数部分的中文字符
            encoded_params = []
            for param in params.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    # 对value进行URL编码
                    encoded_value = quote(value, safe='')
                    encoded_params.append(f"{key}={encoded_value}")
                else:
                    encoded_params.append(param)
            url = f"{base_url}?{'&'.join(encoded_params)}"
        
        request = Request(url)
        request.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15')
        request.add_header('Cookie', COOKIE)
        request.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
        
        response = urlopen(request, timeout=30)
        content = response.read().decode('utf-8')
        return content
    except Exception as e:
        print(f"  ✗ 获取失败: {e}")
        return None

def extract_persons_from_html(html_content):
    """从HTML中提取人物信息"""
    if not html_content:
        return []
    
    persons = []
    
    # 提取所有包含QueryName的<a>标签
    pattern = r'''
        <a\s+[^>]*?
        href="(zp_CV\.aspx[^"]+)"
        [^>]*?>
        .*?
        <span\s+class="QueryName">([^<]+)</span>
        .*?
        </a>
        (.*?)
        (?=<a\s+|<td|</td|</tr|$)
    '''
    
    matches = re.finditer(pattern, html_content, re.VERBOSE | re.DOTALL)
    
    for match in matches:
        url = match.group(1).strip()
        name = match.group(2).strip()
        after_content = match.group(3)
        
        # 提取NID
        nid_match = re.search(r'NId=([^&]+)', url)
        nid = nid_match.group(1) if nid_match else ''
        
        # 提取关系
        relation = ''
        relation_match = re.search(r'<div\s+class="QueryClassName">([^<]*)</div>', match.group(0))
        if relation_match:
            relation = relation_match.group(1).strip()
        
        # 提取备注
        note = ''
        note_matches = re.findall(r'<div\s+class="QueryClassName">([^<]*?)(?:<br/>)?</div>', after_content)
        if note_matches:
            notes = [n.strip() for n in note_matches if n.strip() and n.strip() != relation]
            note = ' '.join(notes)
        
        # 构建完整URL
        full_url = f"http://112.5.13.209:88/wap/{url}"
        
        persons.append({
            'nid': nid,
            'name': name,
            'relation': relation,
            'url': full_url,
            'note': note
        })
    
    # 去重
    seen_nids = set()
    unique_persons = []
    for person in persons:
        if person['nid']:
            if person['nid'] not in seen_nids:
                seen_nids.add(person['nid'])
                unique_persons.append(person)
        else:
            unique_persons.append(person)
    
    return unique_persons

def sanitize_filename(name):
    """清理文件名，移除不合法字符"""
    # 移除或替换文件名中不合法的字符
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    # 限制文件名长度
    if len(name) > 200:
        name = name[:200]
    return name

def save_to_csv(persons, csv_path):
    """保存人物信息到CSV文件"""
    if not persons:
        # 即使没有数据，也创建一个空的CSV文件
        with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['序号', '姓名', '关系', 'URL', '备注', 'NID'])
            writer.writeheader()
        return
    
    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        fieldnames = ['序号', '姓名', '关系', 'URL', '备注', 'NID']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for idx, person in enumerate(persons, 1):
            writer.writerow({
                '序号': idx,
                '姓名': person['name'],
                '关系': person['relation'],
                'URL': person['url'],
                '备注': person['note'],
                'NID': person['nid']
            })

def process_node(node, parent_path='', level=0):
    """
    递归处理JSON节点
    parent_path: 父级路径
    level: 当前层级（用于缩进显示）
    """
    indent = '  ' * level
    name = node['name']
    href = node['href']
    children = node.get('children', [])
    
    # 构建当前目录路径
    current_dir = os.path.join(BASE_DIR, parent_path, sanitize_filename(name))
    
    # 创建目录
    os.makedirs(current_dir, exist_ok=True)
    
    # CSV文件路径
    csv_path = os.path.join(current_dir, f"{sanitize_filename(name)}.csv")
    
    print(f"{indent}[{level}] {name}")
    print(f"{indent}    目录: {current_dir}")
    print(f"{indent}    URL: {href[:80]}...")
    
    # 获取HTML并提取数据
    html_content = fetch_html(href)
    if html_content:
        persons = extract_persons_from_html(html_content)
        save_to_csv(persons, csv_path)
        print(f"{indent}    ✓ 保存CSV: {len(persons)} 人")
    else:
        # 即使失败也创建空CSV
        save_to_csv([], csv_path)
        print(f"{indent}    ✗ 创建空CSV")
    
    # 延迟以避免请求过快
    time.sleep(0.5)
    
    # 递归处理子节点
    if children:
        print(f"{indent}    ↓ 处理 {len(children)} 个子节点...")
        for child in children:
            process_node(child, os.path.join(parent_path, sanitize_filename(name)), level + 1)

def main():
    """主函数"""
    print("开始解析 main_parsed.json 并获取CSV文件...")
    print("=" * 80)
    
    # 读取JSON文件
    json_path = 'main_parsed.json'
    if not os.path.exists(json_path):
        print(f"✗ 错误: 找不到文件 {json_path}")
        return
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"✓ 读取JSON文件: {len(data)} 个顶层节点")
    print(f"✓ 输出目录: {BASE_DIR}/")
    print("=" * 80)
    print()
    
    # 清理并创建基础目录
    if os.path.exists(BASE_DIR):
        print(f"⚠️  目录 {BASE_DIR}/ 已存在，将在其中创建/覆盖文件")
    os.makedirs(BASE_DIR, exist_ok=True)
    
    # 处理每个顶层节点
    total_nodes = len(data)
    for idx, node in enumerate(data, 1):
        print(f"\n{'=' * 80}")
        print(f"处理顶层节点 [{idx}/{total_nodes}]")
        print(f"{'=' * 80}")
        process_node(node, level=0)
    
    print("\n" + "=" * 80)
    print("✓ 全部完成！")
    print(f"  输出目录: {BASE_DIR}/")
    print("=" * 80)

if __name__ == '__main__':
    main()
