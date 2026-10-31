"""DESIGN metadata only. No ctypes, Win32 port, sink or engine implementation."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
PRIOR=HERE.parent/'recovery-step9-verifier-adapters-20261029'
OUT=HERE/'FILE-PORTS-DESIGN-CONTRACT-v1.json'
FREEZE=HERE/'FILE-PORTS-DESIGN-FREEZE-v1.json'
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')
def pin(p):
    raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def write(p,v):
    with p.open('x',encoding='utf-8') as out:json.dump(v,out,sort_keys=True,indent=2);out.write('\n')
def main():
    assert not OUT.exists() and not FREEZE.exists(),'Preserve design versions'
    basis_names=['VERIFIER-ADAPTER-DESIGN-CONTRACT-v1.json','VERIFIER-ADAPTER-PLATFORM-CLARIFICATION-v2.json',
        'VERIFIER-BOOTSTRAP-INTERFACES-SCOPED-ACCEPTANCE-v2.json','VERIFIER-BOOTSTRAP-INTERFACES-PEER-REVIEW-v2.json']
    basis={n:pin(PRIOR/n) for n in basis_names}
    docs={name:'https://learn.microsoft.com/en-us/windows/win32/api/'+path for name,path in {
        'CreateFileW':'fileapi/nf-fileapi-createfilew','GetFileType':'fileapi/nf-fileapi-getfiletype',
        'GetFileInformationByHandleEx':'winbase/nf-winbase-getfileinformationbyhandleex','GetFinalPathNameByHandleW':'fileapi/nf-fileapi-getfinalpathnamebyhandlew',
        'GetFileSizeEx':'fileapi/nf-fileapi-getfilesizeex','ReadFile':'fileapi/nf-fileapi-readfile','CloseHandle':'handleapi/nf-handleapi-closehandle',
        'GetFileAttributesExW':'fileapi/nf-fileapi-getfileattributesexw','FindFirstFileExW':'fileapi/nf-fileapi-findfirstfileexw',
        'FindNextFileW':'fileapi/nf-fileapi-findnextfilew','FindClose':'fileapi/nf-fileapi-findclose','CreateDirectoryW':'fileapi/nf-fileapi-createdirectoryw',
        'WriteFile':'fileapi/nf-fileapi-writefile','FlushFileBuffers':'fileapi/nf-fileapi-flushfilebuffers',
        'FILE_ATTRIBUTE_TAG_INFO':'winbase/ns-winbase-file_attribute_tag_info','WIN32_FILE_ATTRIBUTE_DATA':'fileapi/ns-fileapi-win32_file_attribute_data',
        'WIN32_FIND_DATAW':'minwinbase/ns-minwinbase-win32_find_dataw'}.items()}
    apis=[
        ['CreateFileW','HANDLE',['LPCWSTR','DWORD','DWORD','LPSECURITY_ATTRIBUTES_NULL','DWORD','DWORD','HANDLE_NULL'],'N+F','File slot / CloseHandle'],
        ['GetFileType','DWORD',['HANDLE'],'N+F','No handle; require FILE_TYPE_DISK1'],
        ['GetFileInformationByHandleEx','BOOL',['HANDLE','ENUM32','LPVOID','DWORD'],'N+F','FileAttributeTagInfo9;8-byte output'],
        ['GetFinalPathNameByHandleW','DWORD',['HANDLE','LPWSTR','DWORD','DWORD'],'N+F','One fixed4101-WCHAR buffer; flags0'],
        ['GetFileSizeEx','BOOL',['HANDLE','PLARGE_INTEGER'],'N+F','Exact nonnegative inputsize or outputinitial0'],
        ['ReadFile','BOOL',['HANDLE','LPVOID','DWORD','LPDWORD','LPOVERLAPPED_NULL'],'sum(Ri)','Synchronous original-file only'],
        ['CloseHandle','BOOL',['HANDLE'],'N+F','File slots only; once per known-owned slot'],
        ['GetFileAttributesExW','BOOL',['LPCWSTR','ENUM32','LPVOID'],'U+S','GetFileExInfoStandard0;36-byte output'],
        ['FindFirstFileExW','HANDLE',['LPCWSTR','ENUM32','LPVOID','ENUM32','LPVOID_NULL','DWORD'],'S','FindExInfoBasic1;NameMatch0;flags0;searchslot'],
        ['FindNextFileW','BOOL',['HANDLE','PWIN32_FIND_DATAW'],'sum(Xk)','Only known-owned active searchslot'],
        ['FindClose','BOOL',['HANDLE'],'S','Searchslots only; once per known-owned slot'],
        ['CreateDirectoryW','BOOL',['LPCWSTR','LPSECURITY_ATTRIBUTES_NULL'],'1','One final newleaf under admitted existingparent'],
        ['WriteFile','BOOL',['HANDLE','LPCVOID','DWORD','LPDWORD','LPOVERLAPPED_NULL'],'sum(Wj)','Synchronous owned-output only'],
        ['FlushFileBuffers','BOOL',['HANDLE'],'E+F','Journal complete-record flushes plus one final perfile']]
    typed=[dict(name=a,restype=b,argtypes=c,attempt_bound=d,scope=e,documentation=docs[a]) for a,b,c,d,e in apis]
    assert len(typed)==14
    K=['authority_factory','file_factory','checker_factory','admit','hash_capture','archive','journal','resources','core','consistency','ancestry','universe_initial','universe_final']
    fixed_events=['bootstrap_reserved','bootstrap_handoff_reserved','verifier_reserved','finalization_reserved',
        'candidate_publication_reserved','cleanup_publication_reserved','terminal_publication_plan_reserved']
    s=dict(schema_version=1,port_design_id='finite-original-file-and-exclusive-sink-v1',
        authorization=dict(design_only=True,implementation=False,ctypes_or_SDK_construction=False,live_file_or_target_operations=False,
            original_payload_or_source_qualification=False,network_client_or_download=False,official_documentation_reads_allowed=True),
        trusted_origin=dict(total_seconds=300,work_seconds=295,final_reserve_seconds=5,
            first_action='Trusted frozen entry imports only time prerequisite then captures monotonic t0 before any other imports, authority/source reads/hash, factories or output metadata. Interpreter startup/clock prerequisite are disclosed outside this source clock.',
            continuation='Same accepted owner/nonce/monotonic callable/start/deadlines/output/journal/registry and known early captures; no numeric/JSON restart or crossrun cachedready flag.',
            accepted_source_sha256='d937599212133ee7c036ee863b8c751885ffe60f7d657ec1ed5e506bf90c74eb',
            source_binding='External root pins frozen entry and decision; minimal inline file/output binding trustbase runs under origin. Own modules compile ONLY fresh captured hash-bound bytes in the closed module/dependency map, no normal import/path/cache fallback.',
            platform_trust='Only canonical approved System32 kernel32 binding and approved interpreter/stdlib trust context. Its loading/error-transport internals are disclosed, not claimed absent or universally audited.',
            pending='Real firstentry and productionengine continuation are UNIMPLEMENTED. Frozen engine run_once cannot be called as a new owner or used to lose pre-return platform-slot ownership.'),
        ABI=dict(platform='Windows x64 only; no crossplatform ABI assertion',calling_convention='WINAPI; Microsoft x64 ABI',
            primitive_types=dict(BOOL='signed32',DWORD='unsigned32',ENUM32='signed32',HANDLE='pointer64',LPVOID='pointer64',WCHAR='unsigned16 codeunit',LARGE_INTEGER='signed64',FILETIME='two DWORDs'),
            null_only_parameters='SecurityAttributes/template/overlapped/searchfilter pointers are always NULL; no asynchronous OVERLAPPED structure or inheritablehandle path.',
            structures={
                'FILE_ATTRIBUTE_TAG_INFO':dict(bytes=8,alignment=4,offsets=dict(FileAttributes=0,ReparseTag=4)),
                'WIN32_FILE_ATTRIBUTE_DATA':dict(bytes=36,alignment=4,offsets=dict(dwFileAttributes=0,ftCreationTime=4,ftLastAccessTime=12,ftLastWriteTime=20,nFileSizeHigh=28,nFileSizeLow=32)),
                'WIN32_FIND_DATAW':dict(bytes=592,alignment=4,offsets=dict(dwFileAttributes=0,ftCreationTime=4,ftLastAccessTime=12,ftLastWriteTime=20,nFileSizeHigh=28,nFileSizeLow=32,dwReserved0=36,dwReserved1=40,cFileName=44,cAlternateFileName=564),arrays=dict(cFileName_WCHARs=260,cAlternateFileName_WCHARs=14)),
                'FILETIME':dict(bytes=8,alignment=4,offsets=dict(dwLowDateTime=0,dwHighDateTime=4)),
                'LARGE_INTEGER':dict(bytes=8,alignment=8,meaning='signed64 QuadPart representation'),
                'SECURITY_ATTRIBUTES':dict(bytes=24,alignment=8,offsets=dict(nLength=0,lpSecurityDescriptor=8,bInheritHandle=16),use='NULL only; no instance created by this design')},
            source_text_basis=dict(SDK='10.0.26100.0',root='C:/Program Files (x86)/Windows Kits/10/Include/10.0.26100.0/um',
                files=['fileapi.h','minwinbase.h','winbase.h'],locations=['minwinbase.h114..125 WIN32_FIND_DATAW;138..175 enums;178..195 FileAttributeTagInfo9',
                    'fileapi.h588..595 WIN32_FILE_ATTRIBUTE_DATA','winbase.h9176..9179 FILE_ATTRIBUTE_TAG_INFO'],
                caveat='Source-format read only, no fresh source/ABI qualification. Installed Windows declaration has no obsolete trailing FindData fields despite broader Microsoft synopsis. Future actual ctypes sizes/offsets and bound header identities require a separately reviewed test.'),
            exports=typed,error_transport='Bind use_last_error=True; capture Python-visible raw result/ownership/count first, then ctypes-local error copy before any clock/log/query. Successful BOOL buffer results do not imply OS LastError0: retain error_definedFalse or source-normalized0 convention explicitly. No arbitrary WinDLL or extra fileAPI fallback.'),
        superseded_proposal=dict(base='0327 broad null/zero/INVALID-as-knownfailure rule is superseded FOR THIS prospective platformport.',
            documented_failure='CreateFileW/FindFirstFileExW: only raw INVALID_HANDLE_VALUE(0xffffffffffffffff on thisABI) is documented known nohandle failure.',
            unexpected='NULL/zero/malformed/unreturned is unknown/unqualified, no guessed handle/closer/ownedack. Exact typedOpenFailure only for a known documented nohandle branch.',
            identity='Known valid nonzero/nonINVALID rawhandle becomes owned before all inspection; later failure never erases that slot.'),
        admitted_paths=dict(grammar='Absolute drive-letter DOS scalarUTF16 path, <=4096 UTF16 units excludingNUL; strict source_key-style components, ASCII-only casefold/slash key; no empty/dot/dotdot/trailingdotspace/controls/DEL/device stems/colon-stream/tilde/UNC/deviceprefix/Unicodealias repair.',
            roles='Exact predeclared canonical-collision-free path/role/size/SHA roster. C paths only explicit accepted interpreter/platform/source declarations; project/output/model roles exact approved D roots; protected E rejected. No arbitrary suffix or size exemption.',
            native_name='Use declared DOS spelling. FinalPath flags0 allow only the exact returned extended DOS prefix removal before the same pure comparison; reject UNC/NT/GUID/relative/unexpected or truncated results. Never resolve/repair source aliases by filesystem.',
            ancestor_index='Build exact unique directorynodes from admitted origins, selected runroot dirs and prospective outputleaf before metadata dispatch. U<=1024 includes the outputleaf, queried only after its known creation. Ordinary ancestry observation is not hostile-race/physical-file authentication.',
            no_fallback=['Path.exists/is_symlink/stat/lstat/resolve/rglob','os.path/os.listdir/os.scandir','glob/walk/open/read_bytes/write_bytes','SDK.Kernel32 or launchhelper import/construction','reported module/image path inspection']),
        slots=dict(preallocation='Source-owned finite registry and return/error/buffer slots before each dispatch; rawhandle/result assignment is earliest deliberate Python application work after FFI returns. No atomic/native-to-Python/no-allocation guarantee.',
            kinds={'original_file':'CreateFileW -> CloseHandle','output_file':'CreateFileW -> CloseHandle','file_search':'FindFirstFileExW -> FindClose','namespace':'CreateDirectoryW BOOL, no handle closer'},
            open_states=['reserved','entered_return_unknown','observed_owned','known_failure_no_handle','malformed_or_return_unknown'],
            close_states=['not_attempted','reserved_once','entered_return_unknown','returned_success','returned_failure','not_dispatched_deadline'],
            cleanup='Central owner only. No destructor/contextmanager/identity helper hidden close. Close reservation consumes actionable right once; false/unknown is an authoritative incomplete cleanup with rawvalue retained, never a retry or guessed successful release.',
            ownership_gap='Unobserved API return may have acquired resources; never infer zero sideeffects. Public owner types/nonces are ordinary trusted-source interfaces, not hostilePython isolation.'),
        originals=dict(open=dict(desired_access=2147483648,share_mode=1,creation=3,flags=2097280,security=None,template=None),
            inspection_order=['GetFileType disk1','GetFileInformationByHandleEx FileAttributeTagInfo9 size8; no directory0x10/reparse0x400',
                'GetFinalPathNameByHandleW fixed4101 WCHAR buffer,flags0,0<n<4101 and terminator, exact admitted finalDOS path',
                'GetFileSizeEx exact declared nonnegative signed64 size'],
            inspection_failure='Known file slot remains owned and closes once in unconditionalowner cleanup. Raw BOOL/DWORD/size/path buffers and definedness retained before postcallclock/decoding; no sizeprobe or validation retry.',
            read=dict(chunk_bytes=65536,per_file_cap='Ri=0 whenBi0, otherwise ceil(Bi/65536)+16',aggregate='R=sum Ri from exact future descriptors including early sources once',
                ordering='Reserve pending+requested beforecall. Record visible BOOL/rawDWORD count, observed-return and known-defined count/knownbytes increment before slicing/hash/capture/clock. False/nonreturn count remains undefined even ifrawcell0.',
                success='For positive remainingbytes, require TRUE and strict1..requested count. Successful shortread continues at naturally advanced pointer under cap; TRUE0 before declaredsize is incomplete, not infinite retry. Emptyfilehash has no ReadFile call.',
                late='Known late bytes remain observed; no hash/capture/work after295 cutoff. Last returned buffer remains retained without overwrite. knownbytes/hashedbytes/capturedbytes tracked separately; pending hash update or count mismatch prevents gate.',
                one_pass='Fresh originalhandle starts at0; no seek/reset/reopen/finalweightpass. Capture only declared small roles<=64MiB total; CPU/models streamhash only. All originalleases live through all workgates.'),
            trust_limit='Share-read-only blocks ordinary compatible write/delete opens, not all hostile mapping/namespace/OS mutation. Samehandle observations/fresh bytes are not universal immutable-file authentication.'),
        metadata_scans=dict(scans=2,directories_each_max=8,depth_max=4,non_dot_entries_each_max=64,dot_entries_each_max='2Dk<=16',overflow_witness_each=1,
            ancestor_calls='U+S attributes calls: each unique admitted directoryonce, plus each scan directory immediately before its iterator. Outputleaf is includedU and queried onlyaftercreation; no1041st hiddenextra.',
            attribute_result='GetFileAttributesExW GetFileExInfoStandard0 into unique preallocated36byte record. FALSE output undefined; TRUE directory and no reparse required. Missing/failure/unknown is not safeancestor proof.',
            iterator='Literal admitted_directory+backslash+star, Basic1,NameMatch0,filterNULL,flags0. Validhandle registeredbefore first result interpretation. Each call writes a distinct reserved592byte record so late/failed buffers are not overwritten.',
            order='Retain exact API return order/raw metadata. Count literal . and .. before traversal exclusion; ignorealternate names aslocators. Reject reparse/unknown/unterminated/noncanonical/overdepth/overtype before opening/traversing that entry. Sort a separate index only after complete enumeration.',
            terminal='FindNext FALSE/error18 is naturalend ONLY for established ownediterator; failed bufferundefined. Other false/error/unknown stops incomplete. InitialINVALID/error18 is not naturalend.',
            declared_empty='Only a source-declared expectedempty directory with immediately preceding known directory/no-reparse attrs and initial INVALID_HANDLE_VALUE/error2(ERROR_FILE_NOT_FOUND) may record empty_no_iterator; noFindClose. InitialNULL or anyothererror is incomplete. Two scans/attrs are non-atomic, no hostile-race proof.',
            caps='For eachscan k: Dk exactdeclared dirs<=8; successrecordcap64+2Dk+1 incloverflow; FindFirst capDk; conservative FindNext capXk=64+3Dk+1; FindClose<=Dk. Across scans S=sumDk<=16,X=sumXk<=178.',
            storage='Reserve one592byte outputbuffer per possible First/Next attempt: sum(Dk+Xk)*592<=114848 bytes. Raw failed cells retained undefined; no arbitrary additionaldirectory discovered.',
            universe='Compare exact frozen conditional file/directory roster beforework and beforeworkcompletion; missing, extra or changed entries reject. No additional originals are admitted from a scan; no global/system/process inventory.'),
        output=dict(namespace='One CREATE_NEW-directory attempt at fixed approved parent/key; no recursiveparent creation or reuse. TRUE storesnamespace-owned beforepostclock. FALSE/existing/unknown grants no namespace write authority and no automaticretry.',
            readiness='namespace_owned and reservation_ready are distinct. Keep all partial file/search slots in ownerregistry even when reserveack fails. No original reads until reservationfile knownwrite/flush/close plus initialjournalrecord knownflush; false/unknownready stopswork.',
            names=['reservation.json','journal.jsonl','verification-candidate.json','original-lease-cleanup.json','receipt.json','terminal-seal.json','failure.json','late-failure.json','after-seal-failure.json'],
            open=dict(desired_access=1073741952,share_mode=0,creation=1,flags=128,security=None,template=None),
            before_first_write='Same four fileidentity calls asoriginal, but exact outputpath and size0. GENERIC_WRITE|FILE_READ_ATTRIBUTES grants intended identity access; nofilecontent written before known disk/nonreparse/finalpath identity. No atomicnamespace-race guarantee.',
            write='Reserve exact immutable record bytes/aggregate budget beforedispatch, <=65536 request. Store returned flag/rawcount/known successful positive bytes and offset beforeclock/hash/slicing. TRUEshort writes continue only underfinitecap; TRUE0/false/unknown/invalidcount stops. Never seek/retry failedwrite/overwrite/delete/rename.',
            flush='Knowncomplete journalrow flush beforeack. One finalflush peropenedfile; false/unknown/late flush cannot authorize completion. Outputhashes consume only knownwritten immutablebuffer slices aftersamehardclock gate; nooutputreopen/hashpass.',
            quota=dict(files_max=9,journal_bytes=8388608,journal_record_max=2048,journal_row_bytes=65536,report_files=4,report_bytes_each=2097152,small_files=4,small_bytes_each=8192,total_bytes=16809984,
                WriteFile='Wj=recordcapj+ceil(bytecapj/65536)+16; journalrecordcap=Eplanned, others1; sumWj=Eplanned+412<=2460',
                FlushFileBuffers='Eplanned+F<=2057',file_CloseHandle='N+F<=265'),
            accounting='Reserved bytes are not knownwritten; returnedbytes are not flushed; flushed row is not finalack; keep separate counters. One failedjournal append disables future normalappends, avoiding recursive logging or a repaired chain.',
            postdeadline='No API dispatch afterhard300 cutoff, includingbest-effortfailure callback. Retain in-memory veto/incomplete/nonzero result when marker cannot be published; no new IObudget.'),
        seal_DAG=dict(order=['reservation+firstjournalack','work/source/helper/checker events','nonfinalcandidate knownwrite/flush/close','close originals once','cleanupfile knownwrite/flush/close',
                'last terminalpublication-plan journalrecord;flush+closejournalonce','receipt knownwrite/flush/close','terminalseal knownwrite/flush/close','ownerlocal finalsameclock acknowledgment'],
            edges={'candidate':'Source/input digests and work observations; notfinal authority','cleanup':'Originalclose outcomes and candidatecloseknown',
                'receipt':'Reservation,candidate,cleanup,closedjournal bytes/hash/tip and their knowncloses; exact source/input context; no selfhash',
                'terminalseal':'Receipt and prior fixedartifact map, including receiptclose; excludesitself and lateroptionalvetoes',
                'owner_ack':'Only witness ofseal ownclose/final originalclock+all required gates; never serializedreadiness'},
            vetoes='Every primary/late/aftersealfailure, missing/partial artifact, requiredunknownoperation or finalclock failure vetoespositive eligibility. Preserve immutable primary+latererrors. No journalappend aftersealedtip. Seal alone neverfinalauthority.',
            closure_notice='Currentaccepted engine/source interfaces do not implement this entire DAG/partial-output ownership continuity. Productionbinding remainspending and must be independently source/pure reviewed.'),
        admission_formulas=dict(symbols=dict(N='Allunique originals, including B earlybootstrap leaves once, ceiling256',B='Earlyfresh source/decision originals subsetN, <=16',M='Own source modules compiled from capturedbytes, <=16',
                U='Unique admitted directorynodes incl prospectiveoutputleaf, <=1024',S='sumDk over2scans,<=16',F='Conditional outputfile count,<=9',E='Exact full journal attempt reservation inclfailureheadroom',K=K,F_fixed=fixed_events),
            original_roster='Exactstaticsoftware+4dynamic current-code/evidence leaves+5payload descriptors+allsource-declared owner/archive/bootstrap leaves; canonicaldedup only for identicalrole/size/hash claims. B must matchan adopted subset, not an exemption. Actualroster is NOT provided or assumedfit here.',
            mini_plan='Before firstsource open, admit only externally pinned finite B/output/ancestor/capture/call claims. Charge every operation to originalorigin/globalcaps. No ordinary import to acquire its own authority.',
            full_plan='From fresh source-boundauthority, compute actualN,B,M,U,Dk,allroles/aliases/capture/reportbytes/API/event reservations BEFORE any remainingoriginal open. AdoptknownB slots/digests/captures/liveleases without reread. If graphfails, cleanupknownB; never claimzero bootstrapreads or resetdeadline.',
            events='E=6N+2B+2M+4S+2*len(K)+len(F_fixed)+128 =6N+2B+2M+4S+161; requireE<=2048 and everycanonicalrow<=65536/journal<=8MiB.',
            event_meaning='Normalfile6=openreserve/openreturn/hashreserve/hashreturn/closereserve/closeoutcome; earlyB adds2existingidentityframes. Ownmodulecompile2each; search4each=openreserve/iterationoutcome/closereserve/closeoutcome; Kstagepairs/Ffixed exactlists. No perread/perentry/perport-internaljournal recursion.',
            API_total='6*(N+F)+(U+S)+2S+sumXk+1+sumRi+sumWj+(E+F). All are finite plannedupperbounds, not observedcost/fit.',
            buffer_bound='Capture<=64MiB; one64KiB originalread buffer; fileidentity buffers<=8222*(N+F); metadata36*(U+S); search592*sum(Dk+Xk); plus bounded output/canonical/report buffers. Python/FFI overhead and300sfit unmeasured.',
            report_preflight='Exact source-bound report schemas must preflight worst-case canonical report<=2MiB and outputaggregate quotas BEFORE remainingopens. Count expectedsuccessfulpathmetadata plus onefullbounded failingidentitybuffer; ifnotfit,HOLD, no droppingrecords/capraise.',
            not_current_fit='256files/2048events are ceilings only. No current authority, sourceclosure, outputuniverse or liveprofile fit is established by algebra.'),
        source_and_qualification=dict(originalSDK='3bfac51893b60221728ac915516c5e816c0cfc5a82899f5871f7931469d7fdfd remainsunchanged/harddisabled; noimport or monkeypatch.',
            source_roster='Futureentry/ports/sink/continuation/loader/actualbytecheckers/authority/protocol/pureproofs/rootdecision exactacyclic graph required. No own/currentproof hash in staticmanifest that depends onfinalparent; dynamicanchors separately pinned.',
            typed_return='Only source-bound platformport validates/wraps documented rawresults into exact ownerissued types. Foreign/malformed/rawdict/typednull outcomes never guessedowned/closed.',
            code_gate='Root+independent review ofthis design, then separatelyauthor pure/injectedport source and literalnormal/faultvectors before anyactualctypes/APIqualification.',
            live_gate='Laterrootpermission for finite harmless file-only exactnamespace/flags/partialread-write/cleanup/sourceclock tests. No target/model/profilepermission follows.',
            checker_gaps='Archive/reportbinder, fullresourcegate and newUnicodewire/profilechecker plus productionenginebinding remainpending; journal/resourceprimitives and suppliedpieceanalyzer do not complete them.'),
        required_fake_vectors=['Knownvalid open thenidentity/clock/logfailure retainsownedslot and onceclose','DocumentedINVALIDfailure vs unexpectedNULL/unreturned no guessedclose',
            'NamespaceTRUE thenjournalreservefail keepsnamespace/partialslots butzerooriginalreads','Knownread bytes survive latercopy/hash/deadlinefault; failedrawcountundefined',
            'File/search wrongcloser prohibited; no uncertainclose retry','Initialemptyiterator policy separatefromFindNextnaturalend; unterminated/extra/reparse/overflow paths noopen',
            'Zero/short/failed/unreturned outputwrite andflush withoriginalprimarypreserved','Knownseallatereturn/finalclock failure nofileIOafterhardcutoff',
            'Acycliccandidate/cleanup/journal/receipt/seal selfhash/samepath/unknownveto fail','Exactfutureplan exceedsN/U/E/capture/report/read/write quota holdsbefore remainingoriginals',
            'Foreignport/nonce/serializedready/doublehandoff/cachedownmodule cannot mint sourcegates'],
        documentation=docs,scientific_validation='not_established',implementation_authorized=False,execution_authorized=False)
    assert len(K)==13 and len(fixed_events)==7
    assert 8388608+4*2097152+4*8192==16809984
    assert (2048+128+16)+4*(1+32+16)+4*(1+1+16)==2460
    value=dict(schema_version=1,status='DESIGN_FOR_ROOT_AND_INDEPENDENT_REVIEW_BEFORE_CODE',recorded_at_utc=datetime.now(timezone.utc).isoformat(),
        semantic_contract=s,semantic_sha256=hashlib.sha256(canonical(s)).hexdigest(),basis=basis,author=pin(Path(__file__)),
        source_and_docs_activity='Retained source/metadata and installedSDK declaration TEXT reads plus officialMicrosoft documentation browsing only. No ctypes/API/port/SDK construction, originalinput/sourcequalification, CPU/GGUF/pack/target/compiler/process operation.',
        documentation_retrieval_failures='Initialincorrect fileapi GetFileInformationByHandleEx URL returned404; corrected officialwinbase page suppliedsignature. No source/data artifact fetched or downloaded.')
    write(OUT,value)
    write(FREEZE,dict(schema_version=1,status='DESIGN_FROZEN_FOR_REVIEW_NO_PORT_IMPLEMENTATION',contract=pin(OUT),author=pin(Path(__file__)),semantic_sha256=value['semantic_sha256'],
        direct_file_exports=14,Win32_API_calls=0,old_original_or_source_qualification=0,CPU_GGUF_oldpack_operations=0,implementation_authorized=False,execution_authorized=False))
    print(json.dumps(dict(contract=pin(OUT),freeze=pin(FREEZE),semantic_sha256=value['semantic_sha256'])))
if __name__=='__main__':main()
