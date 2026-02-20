#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提取家谱基本信息：姓名、URL、备注
"""

import re
import csv
import html
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from urllib.error import URLError, HTTPError

def fetch_html_from_url(url, cookie=None):
    """从URL获取HTML内容"""
    try:
        print(f"正在从URL获取HTML...")
        print(f"URL: {url[:100]}...")
        
        # 使用urlencode正确编码URL参数
        if '?' in url:
            base_url, params_str = url.split('?', 1)
            # 解析参数
            params = {}
            for param in params_str.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    params[key] = value
                else:
                    params[param] = ''
            
            # 重新编码
            encoded_params = urlencode(params)
            url = f"{base_url}?{encoded_params}"
        
        request = Request(url)
        request.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.2 Safari/605.1.15')
        request.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
        request.add_header('Accept-Language', 'en-US,en;q=0.9')
        request.add_header('Accept-Encoding', 'gzip, deflate')
        request.add_header('Connection', 'keep-alive')
        request.add_header('Upgrade-Insecure-Requests', '1')
        
        # 添加Cookie（如果提供）
        if cookie:
            request.add_header('Cookie', cookie)
            print(f"✓ 使用Cookie认证")
        
        response = urlopen(request, timeout=30)
        content = response.read().decode('utf-8')
        
        print(f"✓ 成功获取HTML (大小: {len(content)} 字符)")
        return content
    except HTTPError as e:
        print(f"✗ HTTP错误: {e.code}")
        return None
    except URLError as e:
        print(f"✗ URL错误: {e.reason}")
        return None
    except Exception as e:
        print(f"✗ 获取失败: {e}")
        return None

def extract_basic_info(source, fallback_file=None, cookie=None):
    """从HTML文件或URL提取基本信息"""
    
    # 判断source是URL还是文件路径
    if source.startswith('http://') or source.startswith('https://'):
        # 从URL获取
        content = fetch_html_from_url(source, cookie=cookie)
        if not content or len(content) < 1000:  # 如果内容太短，可能是错误页面
            if len(content) > 0 and len(content) < 1000:
                print(f"⚠️  URL返回内容太短 ({len(content)} 字符)，可能是权限错误")
            
            # 尝试使用备用文件
            if fallback_file:
                print(f"\n尝试从备用文件读取: {fallback_file}")
                try:
                    with open(fallback_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    print(f"✓ 成功从备用文件读取 (大小: {len(content)} 字符)")
                except Exception as e:
                    print(f"✗ 读取备用文件失败: {e}")
                    return []
            else:
                print("❌ 无法从URL获取HTML，且没有提供备用文件")
                return []
    else:
        # 从文件读取
        print(f"正在从文件读取HTML: {source}")
        try:
            with open(source, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"✓ 成功读取文件 (大小: {len(content)} 字符)")
        except Exception as e:
            print(f"✗ 读取文件失败: {e}")
            return []
    
    print(f"HTML内容长度: {len(content)} 字符")
    
    # 提取所有的<a>标签及其后续内容
    # 模式：捕获链接、姓名、关系、以及可能的备注信息
    
    persons = []
    
    # 正则模式：提取<a>标签和其内容
    # 匹配格式：<a href="...">...<span class="QueryName">姓名</span>...</a>
    # 只匹配zp_CV.aspx链接，过滤掉zp_XinSiPdf.aspx等其他类型的链接
    pattern = r'''
        <a\s+[^>]*?
        href="(zp_CV\.aspx[^"]+)"     # 只捕获zp_CV.aspx的URL
        [^>]*?>
        .*?
        <span\s+class="QueryName">([^<]+)</span>  # 捕获姓名
        .*?
        </a>
        (.*?)              # 捕获</a>之后的内容（可能包含备注）
        (?=<a\s+|<td|</td|</tr|$)  # 直到下一个<a>或td标签
    '''
    
    matches = re.finditer(pattern, content, re.VERBOSE | re.DOTALL)
    
    for match in matches:
        url = match.group(1).strip()
        name = match.group(2).strip()
        after_content = match.group(3)
        
        # 从URL中提取NID
        nid_match = re.search(r'NId=([^&]+)', url)
        nid = nid_match.group(1) if nid_match else ''
        
        # 提取关系描述（在<a>标签内的QueryClassName）
        relation = ''
        relation_match = re.search(r'<div\s+class="QueryClassName">([^<]*)</div>', match.group(0))
        if relation_match:
            relation = relation_match.group(1).strip()
        
        # 提取备注信息（在</a>之后的qbox1-qbox3结构中的QueryClassName）
        note = ''
        # 在after_content中查找qbox结构中的QueryClassName
        note_matches = re.findall(r'<div\s+class="QueryClassName">([^<]*?)(?:<br/>)?</div>', after_content)
        if note_matches:
            # 过滤掉空白和重复的关系描述
            notes = [n.strip() for n in note_matches if n.strip() and n.strip() != relation]
            note = ' '.join(notes)
        
        # 构建完整URL
        if url.startswith('zp_CV.aspx') or url.startswith('zp_XinSiPdf.aspx'):
            full_url = f"http://112.5.13.209:88/wap/{url}"
        else:
            full_url = url
        
        persons.append({
            'nid': nid,
            'name': name,
            'relation': relation,
            'url': full_url,
            'note': note
        })
    
    print(f"提取到 {len(persons)} 个人物信息（去重前）")
    
    # 去重：根据NID去重，保留第一个出现的记录
    # 对于没有NID的记录，也保留
    seen_nids = set()
    unique_persons = []
    for person in persons:
        if person['nid']:
            # 有NID的记录，进行去重
            if person['nid'] not in seen_nids:
                seen_nids.add(person['nid'])
                unique_persons.append(person)
        else:
            # 没有NID的记录，直接保留
            unique_persons.append(person)
    
    removed_count = len(persons) - len(unique_persons)
    if removed_count > 0:
        print(f"去重移除 {removed_count} 个重复记录")
    print(f"保留 {len(unique_persons)} 个人物信息")
    return unique_persons

def save_to_csv(persons, output_file):
    """保存为CSV文件"""
    
    if not persons:
        print("没有数据可保存")
        return
    
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        # 使用utf-8-sig以便Excel正确显示中文
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
    
    print(f"✓ CSV文件已保存: {output_file}")
    print(f"  包含 {len(persons)} 条记录")

def show_sample(persons, n=5):
    """显示前n条样本数据"""
    print(f"\n前{n}条数据示例:")
    print("=" * 100)
    for i, person in enumerate(persons[:n], 1):
        print(f"\n[{i}] {person['name']}")
        print(f"    关系: {person['relation']}")
        print(f"    备注: {person['note']}")
        print(f"    URL: {person['url'][:80]}...")
        print(f"    NID: {person['nid']}")

if __name__ == '__main__':
    import sys
    import os
    
    # 默认URL和备用文件
    default_url = 'http://112.5.13.209:88/wap/zp_query.aspx?ZId=44638&TId=1&GId=6461&UId=南昌谱源公司&AId=&XId=307&RId='
    fallback_file = '/Users/qixxu01/Downloads/KFA手机族谱.html'
    
    # Cookie（从Safari开发者工具获取）
    cookie = '.SpiderForum=39C3812FF342DDC067C65954D8248E8ED4C6254F5D172DC6BFD5ABB9BE0A06E959273DDFA1ECF55FA0F89C64165A0EDD5EAA7837219A676B5D1F7904C859328064345142A72DCDA78CAF9C17EBD1E720C8B321981C37A4C0334368B26F9FB94AE83E2E87BE293750A6B25051FA31A563FF2487D7909BA3346B0C6FDEFC90B7115947B07A77E27129ED522F3F9F5A618CE42A44E7023E01E196759020DB1277C11E56A7DD; Languages=; MemberId=7e9ae397-b609-45bb-a7cd-4a05f5f69b0c; UserEntityId=15276; UserName=%e5%8d%97%e6%98%8c%e8%b0%b1%e6%ba%90%e5%85%ac%e5%8f%b8; ASP.NET_SessionId=sdk1wdjpk4oxt345esezp1vl'
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        source = sys.argv[1]
    else:
        source = default_url
    
    # 如果提供了第二个参数，作为备用文件路径
    if len(sys.argv) > 2:
        fallback_file = sys.argv[2]
    
    output_file = '/Users/qixxu01/Downloads/family_basic_info.csv'
    
    print("开始提取家谱基本信息...")
    print("=" * 70)
    print(f"数据源: {source[:100]}...")
    if source.startswith('http'):
        if os.path.exists(fallback_file):
            print(f"备用文件: {fallback_file} ✓")
        else:
            print(f"备用文件: {fallback_file} ✗ (文件不存在)")
            print("\n提示: 请提供HTML文件路径作为参数，或将HTML文件放在:")
            print(f"      {fallback_file}")
    print("=" * 70)
    print()
    
    # 提取数据
    persons = extract_basic_info(source, fallback_file=fallback_file if source.startswith('http') else None, cookie=cookie if source.startswith('http') else None)
    
    # 显示样本
    if persons:
        show_sample(persons, 10)
        
        # 保存CSV
        print("\n" + "=" * 70)
        save_to_csv(persons, output_file)
        
        print("\n" + "=" * 70)
        print("✓ 完成！")
        print(f"  共提取 {len(persons)} 人")
        print(f"  CSV文件: {output_file}")
    else:
        print("❌ 未能提取到数据")
