import json,re
from pathlib import Path
p=Path('games/10-kibu10/work/parallel')
s=json.loads((p/'01.source.json').read_text('utf-8-sig'))['units']
d=json.loads((p/'01.trans.json').read_text('utf-8-sig')); old=d['targets'].copy()
r=json.loads((p/'01.review.json').read_text('utf-8-sig'))
for f in r['findings'][1:]:d['targets'][f['id']]=f['suggested_target']
spec='''3+5 6-8 9-10 11-13 14-15 16 17-18 19 20-21 22-24 25 26 27-29 30-31 32
44-45 46 47 48 49-50 51 52 53 54-56 57 58 59
101 102 103-104 105-106 107 108 109-110 111-113 114 115-116 117 118 119 120 121-122 123 124-128 129 130-132 133 134-135 136-137 138-139 140 141-145 146 147-148 149-151 152-155 156 157-158 159 160-164 165-167 168 169 170 171 172-173 174 175 176 178 179 180-182 183-185
197-199 200 201-202 203 205-206 238 262 263 273-274 275 276 277 278 279 280 281 282 283-289 290 291 293 294-296 297 298 299-301 302 303-304 305 306 307-308 309 310 311 312 313 314 315 316 317 318 319-321 322 323 324 327 328 329-330 331 332 333 334 335-338 339 340 341-342 343 344-345 346 347-348 349 350 351 352 353
356 357 358-359 360 361-362 363 364-365 366 367 368 369 370-371 372 373-374 376 377 386 387 388 389-390 391 392 393 394 397-398 401 402 403 408 409 410 420-422 423-424 425-428
447-448 449 450-452 453-454 455-457 458 459 460-461 462 463-465 466 467 468 469 470-472 473-474 475-477 478 479 480 481 482 483 484-485 486 490 491 492 493 494 499-500 501 502 503 504-505 506-507 508 509 510 511 512 513 514-516 517-519 520 521-523 524 525-526 527 528 530-531 532 533 534-535
548 549 550 551 552-553 554 555-557 558 559-561 562-564 565-566 567-568 569 570-571 572 573 574-577 578-579 580 582 583-584 585 586 587-588 589-590 591-592 593 594 595 598-599 600 601 602 603 604-605 606 609 610 611 612 613 614 615 616 617-619 620 621 622-623 624 625-626 627-629 630 631 632-633 634-635 636 637 638 639 640 641 642
646 647 648 649-651 652-653 654-656 657 658 659 660 661 668 669 674 675 690 692 693 694 698 699-700 701 703 704 709 710 711-713 714-715 716 717 718 721 724-725 726 729-730 731 735 736 737-738 742 743 744-745 746 747 748-749 750 751 753 754 758 759 760-761 762-763 764 765-766 767 768 769 771 774 775-776 777-779 780 781-784 785 786-788 789 790 791-792 793 794 795 798 799-800 801 802 803 804 805-806 807 808 809 810-812 813 816 817 818-819 820-822 823-825 826-827 828 829 830-831 832-834 835-836 837 838 844-845 846-847 848-849 850 855-856 858-859 860-862'''
groups=[]; seen=set(); basis={}
for st in spec.split():
 if '+' in st:g=list(map(int,st.split('+')))
 elif '-' in st:a,b=map(int,st.split('-'));g=list(range(a,b+1))
 else:g=[int(st)]
 assert not seen.intersection(g),st
 seen.update(g);groups.append(g)
 for i in g:basis[i]=g
# Embedded quotation belongs within Tailba's complete utterance.
i=182;d['targets'][s[i]['id']]=d['targets'][s[i]['id']].replace('“','‘').replace('”','’')
for g in groups:
 first,last=s[g[0]]['id'],s[g[-1]]['id']
 d['targets'][first]=re.sub(r'(<color=\d+>)',r'\1“',d['targets'][first],count=1)
 t=d['targets'][last];pos=t.rfind('</color>');assert pos>=0
 d['targets'][last]=t[:pos]+'”'+t[pos:]
fixes=[]
for i,u in enumerate(s):
 id=u['id'];t=d['targets'][id]
 assert re.findall(r'<[^>]+>',u['source'])==re.findall(r'<[^>]+>',t),id
 if old[id]!=t:
  reasons=[]
  if i in basis:
   g=basis[i];reasons.append('依据 source-replay 的 NAMAE、完整发言上下文与 BUNKI/TOBU 分支人工确定发言；引号只加在该发言首尾。')
  if i==182:reasons.append('完整发言外层使用双引号，组织名嵌套改用单引号。')
  if any(f['id']==id for f in r['findings'][1:]):reasons.append(next(f['issue'] for f in r['findings'][1:] if f['id']==id))
  fixes.append({'id':id,'index':i,'source':u['source'],'before':old[id],'after':t,'utterance_ids':[s[n]['id'] for n in basis.get(i,[])],'basis':reasons})
notes=['已人工阅读三个脚本的 NAMAE、分支和全部中文上下文，按完整发言分组，非按2E点击加成对引号。','62–86、264–265、395–396、429、495–496、529、596–597、607–608、695–697、702、719–720、732–734、752、770、796–797等调查菜单叙述不沿用线性遍历残留说话人。','492/493、692/693、767/768之间有可跳过后段的条件分支，各自闭合。762–763与764之间为回答分支汇合，分开闭合。','716下令联系后717为联系完成后的报告，各自闭合。3和5跨INFO姓名显示但仍为同一发言。','保留2E/3A/3B出现时机及标签序列；不跨点击搬译文。五项语义和着色修正来自独立审校并已逐项应用。']
(p/'01.trans.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf-8')
(p/'01.quote-fixes.json').write_text(json.dumps({'batch':1,'reviewer':'trans01','changes':fixes,'utterances':[[s[n]['id'] for n in g] for g in groups],'notes':notes},ensure_ascii=False,indent=2)+'\n','utf-8')
print(len(fixes),'changed units;',len(groups),'utterances;',len(seen),'dialogue units')
