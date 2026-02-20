#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import re
import json
import time
import urllib.request
import urllib.parse
import os

# Cookie配置
COOKIE = '.SpiderForum=39C3812FF342DDC067C65954D8248E8ED4C6254F5D172DC6BFD5ABB9BE0A06E959273DDFA1ECF55FA0F89C64165A0EDD5EAA7837219A676B5D1F7904C859328064345142A72DCDA78CAF9C17EBD1E720C8B321981C37A4C0334368B26F9FB94AE83E2E87BE293750A6B25051FA31A563FF2487D7909BA3346B0C6FDEFC90B7115947B07A77E27129ED522F3F9F5A618CE42A44E7023E01E196759020DB1277C11E56A7DD; Languages=; MemberId=7e9ae397-b609-45bb-a7cd-4a05f5f69b0c; UserEntityId=15276; UserName=%e5%8d%97%e6%98%8c%e8%b0%b1%e6%ba%90%e5%85%ac%e5%8f%b8; ASP.NET_SessionId=sdk1wdjpk4oxt345esezp1vl'

def fetch_person_page(url):
    """获取个人详情页HTML"""
    try:
        # 解析URL，对中文参数进行编码
        if '?' in url:
            base_url, params_str = url.split('?', 1)
            params = {}
            for param in params_str.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    params[key] = value
            
            # 重新编码URL
            encoded_params = urllib.parse.urlencode(params, encoding='utf-8')
            url = f"{base_url}?{encoded_params}"
        
        headers = {
            'Cookie': COOKIE,
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.2 Safari/605.1.15'
        }
        
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            html = response.read().decode('utf-8')
            return html
    except Exception as e:
        return None

def parse_person_details(html, nid, name_from_csv, note_from_csv=''):
    """解析个人详情页，提取所有信息"""
    if not html:
        return None
    
    result = {
        'nid': nid,
        'name': name_from_csv,
        'generation': None,
        'url': None,
        'note': note_from_csv if note_from_csv else None,
        'father': None,
        'relation_to_father': None,
        'children': [],
        'siblings': None,
        'detail_info': {
            'raw_text': None,
            'aliases': {},
            'birth': None,
            'death': None,
            'burial': None,
            'migration': None,
            'description': None
        },
        'spouse': None
    }
    
    # 1. 提取世代信息
    generation_match = re.search(r'第(\d+)世</font>', html)
    if generation_match:
        result['generation'] = int(generation_match.group(1))
    
    # 2. 提取与父亲的关系
    relation_match = re.search(r'<font color=blue>([^<]+)</font>&nbsp;?([^&<]+?)&nbsp;?<font color=blue>' + re.escape(name_from_csv), html, re.DOTALL)
    if relation_match:
        relation = relation_match.group(2).strip()
        result['relation_to_father'] = relation if relation else None
    
    # 3. 提取父亲信息
    father_section = re.search(r'父亲.*?<a[^>]+href="([^"]+)"[^>]*>.*?<font color=blue>([^<]+)</font>', html, re.DOTALL)
    if father_section:
        father_url = father_section.group(1)
        father_name = father_section.group(2).strip()
        father_nid_match = re.search(r'NId=([^&]+)', father_url)
        father_nid = father_nid_match.group(1) if father_nid_match else None
        
        result['father'] = {
            'nid': father_nid,
            'name': father_name,
            'url': f"http://112.5.13.209:88/wap/{father_url}"
        }
    
    # 4. 提取子女信息
    children_section = re.search(r'子女.*?</legend>(.*?)</fieldset>', html, re.DOTALL)
    if children_section:
        child_pattern = r'<a[^>]+href="([^"]+)"[^>]*>.*?<div class="CvChilName">([^<]+)</div>'
        child_matches = re.finditer(child_pattern, children_section.group(1), re.DOTALL)
        
        for match in child_matches:
            child_url = match.group(1).strip()
            child_full_name = match.group(2).strip()
            
            # 清理可能的HTML实体
            child_full_name = re.sub(r'&nbsp;?', '', child_full_name)
            
            # 解析关系和姓名
            child_name_match = re.match(r'(.*?)([\u4e00-\u9fa5]{1,4})$', child_full_name)
            if child_name_match:
                child_relation = child_name_match.group(1).strip()
                child_name = child_name_match.group(2).strip()
            else:
                child_relation = ''
                child_name = child_full_name
            
            child_nid_match = re.search(r'NId=([^&]+)', child_url)
            child_nid = child_nid_match.group(1) if child_nid_match else None
            
            result['children'].append({
                'nid': child_nid,
                'name': child_name,
                'relation': child_relation,
                'url': f"http://112.5.13.209:88/wap/{child_url}"
            })
    
    # 5. 提取兄弟姐妹信息
    siblings_section = re.search(r'在兄弟姐妹中排行.*?</legend>(.*?)</fieldset>', html, re.DOTALL)
    if siblings_section:
        content = siblings_section.group(1)
        sibling_pattern = r'([\u4e00-\u9fa5]+子)&nbsp<strong>([^<]+)</strong>'
        all_siblings = re.findall(sibling_pattern, content)
        
        # 找到本人的排行
        rank = None
        for i, (relation, name) in enumerate(all_siblings, 1):
            if name == name_from_csv or f'<font color=red>{relation}' in content:
                rank = i
                break
        
        result['siblings'] = {
            'total_count': len(all_siblings),
            'rank': rank,
            'list': [f"{rel} {name}" for rel, name in all_siblings]
        }
    
    # 6. 提取"入谱人详细信息"完整文本
    detail_section = re.search(r'入谱人详细信息.*?</legend>\s*(.*?)\s*<br\s*/>', html, re.DOTALL)
    if detail_section:
        raw_html = detail_section.group(1)
        detail_text = re.sub(r'<[^>]+>', ' ', raw_html)
        detail_text = re.sub(r'&nbsp;?', ' ', detail_text)
        detail_text = re.sub(r'\s+', ' ', detail_text).strip()
        result['detail_info']['raw_text'] = detail_text
        
        # 如果没有提取到完整内容，尝试更宽松的匹配
        if len(detail_text) < 20:
            detail_section2 = re.search(r'PanelNamememo.*?</legend>(.*?)</fieldset>', html, re.DOTALL)
            if detail_section2:
                raw_html = detail_section2.group(1)
                detail_text = re.sub(r'<[^>]+>', ' ', raw_html)
                detail_text = re.sub(r'&nbsp;?', ' ', detail_text)
                detail_text = re.sub(r'\s+', ' ', detail_text).strip()
                detail_text = re.sub(r'多媒体相关.*$', '', detail_text).strip()
                result['detail_info']['raw_text'] = detail_text
        
        # 提取结构化信息
        if result['detail_info']['raw_text']:
            detail_text = result['detail_info']['raw_text']
            
            # 提取讳
            hui_match = re.search(r'讳([^\s号]+)', detail_text)
            if hui_match:
                result['detail_info']['aliases']['hui'] = hui_match.group(1)
            
            # 提取号
            hao_match = re.search(r'号([^\s]+)', detail_text)
            if hao_match:
                result['detail_info']['aliases']['hao'] = hao_match.group(1)
            
            # 提取出生信息
            birth_match = re.search(r'生于\s*(.*?)\s*(?:殁于|葬|娶|生子|$)', detail_text)
            if birth_match:
                result['detail_info']['birth'] = birth_match.group(1).strip()
            
            # 提取去世信息
            death_match = re.search(r'殁于\s*(.*?)\s*(?:葬|娶|生子|$)', detail_text)
            if death_match:
                result['detail_info']['death'] = death_match.group(1).strip()
            
            # 提取安葬信息
            burial_match = re.search(r'葬(.*?)(?:娶|生子|配|第\d+世|$)', detail_text)
            if burial_match:
                result['detail_info']['burial'] = burial_match.group(1).strip()
            
            # 提取迁徙信息
            migration_match = re.search(r'迁([^\s。]+)', detail_text)
            if migration_match:
                result['detail_info']['migration'] = migration_match.group(1).strip()
    
    # 7. 提取配偶信息
    spouse_section = re.search(r'配偶信息.*?</legend>(.*?)</fieldset>', html, re.DOTALL)
    if spouse_section:
        spouse_html = spouse_section.group(1)
        spouse_text = re.sub(r'<[^>]+>', ' ', spouse_html)
        spouse_text = re.sub(r'\s+', ' ', spouse_text).strip()
        
        if spouse_text:
            spouse_name_match = re.search(r'娶([^\s氏]+氏)', result['detail_info']['raw_text'] or '')
            result['spouse'] = {
                'name': spouse_name_match.group(1) if spouse_name_match else None,
                'detail': spouse_text if spouse_text else None
            }
    
    return result

def main():
    """处理全部673条数据"""
    print("="*80)
    print("开始处理族谱数据（全部673条）".center(76))
    print("="*80)
    
    csv_file = '/Users/qixxu01/Downloads/family_basic_info.csv'
    output_file = '/Users/qixxu01/Downloads/family_tree_full2.json'
    progress_file = '/Users/qixxu01/Downloads/family_tree_progress.json'
    
    # 读取CSV文件
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        all_records = list(reader)
    
    print(f"\n📊 共读取 {len(all_records)} 条记录")
    
    # 检查是否有进度文件
    results = []
    start_index = 0
    if os.path.exists(progress_file):
        print(f"📁 发现进度文件，继续上次的处理...")
        with open(progress_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
            results = saved_data['results']
            start_index = saved_data['last_index'] + 1
            print(f"✅ 已加载 {len(results)} 条记录，从第 {start_index + 1} 条继续\n")
    else:
        print(f"🆕 开始全新处理\n")
    
    # 统计信息
    success_count = len(results)
    fail_count = 0
    
    try:
        for i in range(start_index, len(all_records)):
            record = all_records[i]
            name = record['姓名']
            url = record['URL']
            nid = record['NID']
            note = record.get('备注', '')
            
            print(f"[{i+1}/{len(all_records)}] {name} (NID: {nid[:8]}...)", end=' ')
            
            # 获取详情页
            html = fetch_person_page(url)
            if not html:
                print(f"❌ 获取失败")
                fail_count += 1
                continue
            
            # 解析数据
            person_data = parse_person_details(html, nid, name, note)
            if person_data:
                results.append(person_data)
                success_count += 1
                print(f"✅ 世代:{person_data['generation']} 父:{person_data['father']['name'] if person_data['father'] else '无'} 子:{len(person_data['children'])}人")
            else:
                print(f"❌ 解析失败")
                fail_count += 1
            
            # 每10条保存一次进度
            if (i + 1) % 10 == 0:
                with open(progress_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'results': results,
                        'last_index': i,
                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                    }, f, ensure_ascii=False, indent=2)
                print(f"    💾 已保存进度 ({success_count}成功/{fail_count}失败)")
            
            # 延迟避免请求过快
            time.sleep(0.3)
    
    except KeyboardInterrupt:
        print(f"\n\n⚠️  用户中断！正在保存当前进度...")
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump({
                'results': results,
                'last_index': i,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }, f, ensure_ascii=False, indent=2)
        print(f"✅ 进度已保存到: {progress_file}")
        print(f"📊 已处理: {len(results)} 条记录")
        return
    
    # 保存最终结果
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # 删除进度文件
    if os.path.exists(progress_file):
        os.remove(progress_file)
    
    print(f"\n{'='*80}")
    print(f"✅ 处理完成！")
    print(f"📁 已保存到: {output_file}")
    print(f"📊 成功: {success_count} 条")
    print(f"📊 失败: {fail_count} 条")
    print(f"📊 总计: {len(all_records)} 条")
    print(f"{'='*80}\n")

if __name__ == '__main__':
    main()
