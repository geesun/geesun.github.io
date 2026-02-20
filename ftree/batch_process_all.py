#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import re
import json
import time
import urllib.request
import urllib.parse
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Cookie配置
COOKIE = '.SpiderForum=39C3812FF342DDC067C65954D8248E8ED4C6254F5D172DC6BFD5ABB9BE0A06E959273DDFA1ECF55FA0F89C64165A0EDD5EAA7837219A676B5D1F7904C859328064345142A72DCDA78CAF9C17EBD1E720C8B321981C37A4C0334368B26F9FB94AE83E2E87BE293750A6B25051FA31A563FF2487D7909BA3346B0C6FDEFC90B7115947B07A77E27129ED522F3F9F5A618CE42A44E7023E01E196759020DB1277C11E56A7DD; Languages=; MemberId=7e9ae397-b609-45bb-a7cd-4a05f5f69b0c; UserEntityId=15276; UserName=%e5%8d%97%e6%98%8c%e8%b0%b1%e6%ba%90%e5%85%ac%e5%8f%b8; ASP.NET_SessionId=sdk1wdjpk4oxt345esezp1vl'

# 线程锁用于打印输出
print_lock = threading.Lock()

def thread_print(*args, **kwargs):
    """线程安全的打印函数"""
    with print_lock:
        print(*args, **kwargs)

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
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')
            return html
    except Exception as e:
        return None, str(e)

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

def find_all_csv_files(base_dir):
    """递归查找所有CSV文件"""
    csv_files = []
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.csv'):
                csv_path = os.path.join(root, file)
                csv_files.append(csv_path)
    return csv_files

def process_single_record(record, index, total):
    """处理单条记录（供线程池调用）"""
    name = record.get('姓名', '')
    url = record.get('URL', '')
    nid = record.get('NID', '')
    note = record.get('备注', '')
    
    if not url or not nid:
        return None, f"[{index}/{total}] {name} ⚠️ 跳过（无URL或NID）"
    
    # 获取详情页
    fetch_result = fetch_person_page(url)
    if isinstance(fetch_result, tuple):
        html, err = fetch_result
        return None, f"[{index}/{total}] {name} ❌ 网络错误: {err}  URL: {url}"
    html = fetch_result
    if not html:
        return None, f"[{index}/{total}] {name} ❌ 返回空内容  URL: {url}"
    
    # 解析数据
    person_data = parse_person_details(html, nid, name, note)
    if person_data:
        return person_data, f"[{index}/{total}] {name} ✅"
    else:
        return None, f"[{index}/{total}] {name} ❌ 解析失败（HTML长度:{len(html)}）  URL: {url}"

def process_csv_to_json(csv_file, max_workers=10):
    """处理单个CSV文件，生成对应的JSON文件（使用多线程）"""
    json_file = csv_file.replace('.csv', '.json')
    
    try:
        # 读取CSV文件
        thread_print(f"  📖 读取CSV文件...")
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            all_records = list(reader)
        thread_print(f"  ✓ 读取成功，共 {len(all_records)} 条记录")
    except Exception as e:
        thread_print(f"  ❌ 读取CSV失败: {e}")
        # 即使读取失败，也尝试创建一个空JSON
        try:
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
            thread_print(f"  ⚠️  已创建空JSON文件")
        except:
            pass
        return False
    
    if not all_records:
        thread_print(f"  ⚠️  CSV文件为空，创建空JSON")
        try:
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
            thread_print(f"  ✅ 已创建空JSON: {os.path.basename(json_file)}")
            return True
        except Exception as e:
            thread_print(f"  ❌ 创建JSON失败: {e}")
            return False
    
    # 先加载已存在的JSON结果（用于续跑/补缺）
    results = []
    processed_nids = set()

    if os.path.exists(json_file):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                existing_results = json.load(f)
                if isinstance(existing_results, list):
                    results.extend(existing_results)
                    processed_nids.update(r.get('nid') for r in existing_results if r.get('nid'))
                    thread_print(f"  ↻ 已加载现有JSON: {len(existing_results)} 条记录")
        except Exception as e:
            thread_print(f"  ⚠️  现有JSON读取失败，将重新生成: {e}")

    
    # 过滤出未处理的记录（以NID为准）
    pending_records = []
    for i, record in enumerate(all_records):
        nid = record.get('NID', '')
        if nid and nid in processed_nids:
            continue  # 跳过已处理的
        pending_records.append((i, record))
    
    if not pending_records:
        thread_print(f"  ✅ CSV中所有NID均已在JSON中，无需更新")
        return True
    
    thread_print(f"  🔄 使用 {max_workers} 个线程处理剩余 {len(pending_records)} 条记录...")
    
    success_count = len(results)  # 之前已完成的
    fail_count = 0
    skip_count = 0
    new_success = 0
    
    # 使用线程锁保护results列表
    results_lock = threading.Lock()
    
    try:
        # 使用线程池并发处理
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_record = {
                executor.submit(process_single_record, record, idx+1, len(all_records)): (idx, record)
                for idx, record in pending_records
            }
            
            # 收集结果
            completed = 0
            for future in as_completed(future_to_record, timeout=60):
                try:
                    person_data, msg = future.result(timeout=15)
                    thread_print(f"    {msg}")
                    
                    # 线程安全地添加结果
                    with results_lock:
                        if person_data:
                            results.append(person_data)
                            new_success += 1
                        else:
                            if "跳过" in msg:
                                skip_count += 1
                            else:
                                fail_count += 1
                    
                    completed += 1
                    
                    # 小延迟避免请求过快
                    time.sleep(0.05)
                except TimeoutError:
                    thread_print(f"    ❌ 处理超时（将跳过，重新运行可补缺）")
                    with results_lock:
                        fail_count += 1
                except Exception as e:
                    thread_print(f"    ❌ 处理异常: {e}")
                    with results_lock:
                        fail_count += 1
        
        thread_print(f"  📊 本次处理: {new_success}成功 {fail_count}失败 {skip_count}跳过")
    
    except KeyboardInterrupt:
        thread_print(f"\n  ⚠️  用户中断！等待正在处理的线程完成...")

        # 等待正在执行的任务完成
        executor.shutdown(wait=True, cancel_futures=False)

        thread_print(f"  ✓ 线程已停止，已处理 {new_success} 条新记录")

        # 不要re-raise，继续保存当前结果到JSON
    except Exception as e:
        thread_print(f"  ❌ 线程池异常: {e}")
        import traceback
        thread_print(traceback.format_exc())
    
    # 保存最终结果
    thread_print(f"  💾 保存JSON文件: {os.path.basename(json_file)}")
    try:
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        total_success = len(results)
        thread_print(f"  ✅ 已保存: {total_success} 条记录 → {os.path.basename(json_file)}")
        
        if len(results) + fail_count + skip_count < len(all_records):
            thread_print(f"  💡 提示: 重新运行会基于现有JSON继续补缺")
        
        return True
    except Exception as e:
        thread_print(f"  ❌ 保存JSON失败: {e}")
        import traceback
        thread_print(traceback.format_exc())
        return False

def main():
    """遍历parsed_genealogy目录，将所有CSV转换为JSON（多线程版本）"""
    print("="*80)
    print("批量处理 parsed_genealogy 目录下的CSV文件（多线程）".center(76))
    print("="*80)
    
    base_dir = 'parsed_genealogy'
    max_workers = 5  # 每个CSV文件内部使用5个线程
    
    if not os.path.exists(base_dir):
        print(f"\n❌ 错误: 目录不存在: {base_dir}")
        return
    
    # 查找所有CSV文件
    csv_files = find_all_csv_files(base_dir)
    
    if not csv_files:
        print(f"\n⚠️  在 {base_dir} 中没有找到CSV文件")
        return
    
    # 统计有/没有JSON的文件（仅用于显示，全部都需处理）
    with_json = [f for f in csv_files if os.path.exists(f.replace('.csv', '.json'))]
    without_json = [f for f in csv_files if not os.path.exists(f.replace('.csv', '.json'))]

    print(f"\n📊 找到 {len(csv_files)} 个CSV文件")
    print(f"  · 已有JSON（将检查补缺）: {len(with_json)} 个")
    print(f"  · 无JSON（全新处理）: {len(without_json)} 个")
    print(f"⚡ 使用 {max_workers} 个线程并发处理")
    print("="*80)
    
    # 顺序处理每个CSV文件（但文件内部使用多线程）
    success_files = 0
    fail_files = 0
    
    try:
        for idx, csv_file in enumerate(csv_files, 1):
            # 相对路径显示
            rel_path = os.path.relpath(csv_file, base_dir)
            thread_print(f"\n[{idx}/{len(csv_files)}] {rel_path}")
            
            try:
                # 处理CSV（内部使用5个线程）
                if process_csv_to_json(csv_file, max_workers=max_workers):
                    success_files += 1
                else:
                    fail_files += 1
            except KeyboardInterrupt:
                # 从内层传上来的中断，直接重新抛出
                raise
            except Exception as e:
                thread_print(f"  ❌ 处理异常: {e}")
                import traceback
                thread_print(traceback.format_exc())
                fail_files += 1
    
    except KeyboardInterrupt:
        print(f"\n\n⚠️  用户中断！")
        print(f"📊 本次成功: {success_files} 个文件")
        print(f"📊 本次失败: {fail_files} 个文件")
        print(f"📊 剩余未处理: {len(csv_files) - success_files - fail_files} 个文件")
        print(f"\n💡 提示: 重新运行脚本将继续补缺未完成的文件")
        return
    
    print(f"\n{'='*80}")
    print(f"✅ 全部处理完成！")
    print(f"📊 成功: {success_files}/{len(csv_files)} 个文件")
    if fail_files > 0:
        print(f"📊 失败: {fail_files}/{len(csv_files)} 个文件")
    print(f"{'='*80}\n")

if __name__ == '__main__':
    main()
