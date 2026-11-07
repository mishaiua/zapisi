#!/usr/bin/env python3
"""Собирает файл быстрой команды «Записи» (plist), который потом подписывается:
   python3 tools/make_shortcut.py out.shortcut [ID-календаря]
   shortcuts sign --mode anyone --input out.shortcut --output Записи.shortcut

Команда получает JSON {"events":[{"title","start","end","notes"}]},
удаляет события календаря «Пациенты» с начала сегодняшнего дня и добавляет события из JSON.
"""
import plistlib, uuid, sys

U = lambda: str(uuid.uuid4()).upper()
CAL_ID = sys.argv[2] if len(sys.argv) > 2 else ''


def att(v):
    return {"Value": v, "WFSerializationType": "WFTextTokenAttachment"}


def out(u, name):
    return {"Type": "ActionOutput", "OutputUUID": u, "OutputName": name}


def tok(v):
    return {"Value": {"string": "￼", "attachmentsByRange": {"{0, 1}": v}},
            "WFSerializationType": "WFTextTokenString"}


def A(ident, **p):
    return {"WFWorkflowActionIdentifier": "is.workflow.actions." + ident, "WFWorkflowActionParameters": p}


cal = {"Title": "Пациенты", "Identifier": CAL_ID, "IsAllCalendar": False}
uDict, uList, uStart, uFind, grp, gIf = U(), U(), U(), U(), U(), U()
ri = {"Type": "Variable", "VariableName": "Repeat Item"}

acts = [
    A("detect.dictionary", UUID=uDict, WFInput=att({"Type": "ExtensionInput"})),
    A("getvalueforkey", UUID=uList, WFInput=att(out(uDict, "Словарь")),
      WFDictionaryKey="events", WFGetDictionaryValueType="Value"),
    A("adjustdate", UUID=uStart, WFDate=tok({"Type": "CurrentDate"}), WFAdjustOperation="Get Start of Day"),
    A("filter.calendarevents", UUID=uFind, WFContentItemFilter={
        "WFSerializationType": "WFContentPredicateTableTemplate",
        "Value": {
            "WFActionParameterFilterPrefix": 1,
            "WFContentPredicateBoundedDate": False,
            "WFActionParameterFilterTemplates": [
                {"Operator": 4, "Property": "Calendar", "Removable": True, "Values": {"Calendar": cal}},
                {"Operator": 2, "Property": "Start Date", "Removable": True,
                 "Values": {"Date": tok(out(uStart, "Скорректированная дата")), "Unit": 4}},
            ]}}),
    # удалять, только если что-то нашлось: «Удалить события» без входа может остановить команду
    A("conditional", GroupingIdentifier=gIf, WFControlFlowMode=0, WFCondition=100,
      WFInput={"Type": "Variable", "Variable": att(out(uFind, "События календаря"))}),
    A("removeevents", WFInputEvents=att(out(uFind, "События календаря")), WFCalendarIncludeFutureEvents=False),
    A("conditional", GroupingIdentifier=gIf, WFControlFlowMode=2, UUID=U()),
    A("repeat.each", GroupingIdentifier=grp, WFControlFlowMode=0, WFInput=att(out(uList, "Значение словаря"))),
]
ids = {}
for k in ["title", "start", "end", "notes"]:
    ids[k] = U()
    acts.append(A("getvalueforkey", UUID=ids[k], WFInput=att(ri), WFDictionaryKey=k, WFGetDictionaryValueType="Value"))
acts.append(A("addnewevent",
              WFCalendarItemTitle=tok(out(ids["title"], "Значение словаря")),
              WFCalendarDescriptor=cal,
              WFCalendarItemStartDate=tok(out(ids["start"], "Значение словаря")),
              WFCalendarItemEndDate=tok(out(ids["end"], "Значение словаря")),
              WFCalendarItemNotes=tok(out(ids["notes"], "Значение словаря")),
              WFAlertTime="1 hour before", ShowWhenRun=False, WFCalendarItemAllDay=False))
add_idx = len(acts) - 1
acts.append(A("repeat.each", GroupingIdentifier=grp, WFControlFlowMode=2, UUID=U()))

wf = {
    "WFWorkflowActions": acts,
    "WFWorkflowClientVersion": "2302.0.4",
    "WFWorkflowMinimumClientVersion": 900,
    "WFWorkflowMinimumClientVersionString": "900",
    "WFWorkflowIcon": {"WFWorkflowIconStartColor": 4282601983, "WFWorkflowIconGlyphNumber": 59511},
    # при установке iPhone попросит выбрать календарь (ID календаря на каждом устройстве свой)
    "WFWorkflowImportQuestions": [{"ActionIndex": add_idx, "Category": "Parameter", "DefaultValue": cal,
                                   "ParameterKey": "WFCalendarDescriptor",
                                   "Text": "Выберите календарь «Пациенты»"}],
    "WFWorkflowInputContentItemClasses": ["WFStringContentItem"],
    "WFWorkflowTypes": [],
    "WFWorkflowOutputContentItemClasses": [],
    "WFWorkflowHasShortcutInputVariables": True,
    "WFQuickActionSurfaces": [],
}
plistlib.dump(wf, open(sys.argv[1], 'wb'), fmt=plistlib.FMT_BINARY)
