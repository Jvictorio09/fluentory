# Arabic Translation Format Guide

## File Format: `locale/ar/LC_MESSAGES/django.po`

This document shows the correct format for adding Arabic translations manually.

## Structure

Each translation entry follows this format:

```po
#: file_path:line_number
msgid "English text"
msgstr "Arabic translation"
```

## Complete Example Entry

```po
#: .\myApp\templates\admin\base_site.html:22
msgid "Dashboard"
msgstr "لوحة التحكم"
```

## Current Translations (8 strings)

Here are the 8 strings with their Arabic translations:

### 1. Django site admin
```po
msgid "Django site admin"
msgstr "إدارة موقع Django"
```

### 2. Django administration
```po
msgid "Django administration"
msgstr "إدارة Django"
```

### 3. Welcome,
```po
msgid "Welcome,"
msgstr "مرحباً،"
```

### 4. Dashboard
```po
msgid "Dashboard"
msgstr "لوحة التحكم"
```

### 5. View site
```po
msgid "View site"
msgstr "عرض الموقع"
```

### 6. Documentation
```po
msgid "Documentation"
msgstr "التوثيق"
```

### 7. Change password
```po
msgid "Change password"
msgstr "تغيير كلمة المرور"
```

### 8. Log out
```po
msgid "Log out"
msgstr "تسجيل الخروج"
```

## Header Section (Metadata)

The file header should look like this:

```po
# Fluentory Arabic Translation
# Copyright (C) 2026 Fluentory
msgid ""
msgstr ""
"Project-Id-Version: Fluentory 1.0\n"
"Report-Msgid-Bugs-To: \n"
"POT-Creation-Date: 2026-01-13 05:10+0800\n"
"PO-Revision-Date: 2026-01-13 05:10+0800\n"
"Last-Translator: \n"
"Language-Team: Arabic\n"
"Language: ar\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=UTF-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Plural-Forms: nplurals=6; plural=n==0 ? 0 : n==1 ? 1 : n==2 ? 2 : n%100>=3 "
"&& n%100<=10 ? 3 : n%100>=11 && n%100<=99 ? 4 : 5;\n"
```

## Important Rules

1. **Always keep `msgid` in English** - This is the source language
2. **Put Arabic translation in `msgstr`** - This is what users will see
3. **Keep the quotes** - Both `msgid` and `msgstr` must be in quotes
4. **Use UTF-8 encoding** - Make sure your editor saves as UTF-8
5. **Empty `msgstr ""` means not translated** - Django will show English if empty
6. **Don't change file paths/comments** - The `#:` lines show where strings come from

## Common Arabic Translations Reference

| English | Arabic |
|---------|--------|
| Dashboard | لوحة التحكم |
| Welcome | مرحباً |
| Log out | تسجيل الخروج |
| Login | تسجيل الدخول |
| Sign up | إنشاء حساب |
| Password | كلمة المرور |
| Change password | تغيير كلمة المرور |
| Save | حفظ |
| Cancel | إلغاء |
| Delete | حذف |
| Edit | تعديل |
| View | عرض |
| Courses | الدورات |
| My Courses | دوراتي |
| Settings | الإعدادات |
| Profile | الملف الشخصي |
| Home | الرئيسية |
| Back | رجوع |
| Next | التالي |
| Previous | السابق |
| Search | بحث |
| Filter | تصفية |
| Documentation | التوثيق |
| Help | مساعدة |
| Contact | اتصل بنا |
| About | حول |
| Submit | إرسال |
| Reset | إعادة تعيين |

## After Adding Translations

1. **Save the file** as UTF-8 encoding
2. **Compile translations:**
   ```bash
   python manage.py compilemessages
   ```
3. **Restart your server** to see changes
4. **Test by switching language** using the language switcher

## Adding More Translations Later

When you add `{% trans %}` tags to templates and run `makemessages` again, new entries will be added automatically. Just fill in the `msgstr` fields with Arabic translations.




