# Ubuntu 22.04+ RDP + XFCE 설치 매뉴얼

## 1. 시스템 업데이트

```bash
sudo apt update && sudo apt upgrade -y
```

## 2. XRDP 및 XFCE 설치

```bash
sudo apt install xrdp xfce4 xfce4-terminal dbus-x11 -y
```

## 3. XRDP 서비스 활성화 및 확인

```bash
sudo systemctl enable xrdp
sudo systemctl start xrdp
sudo systemctl status xrdp
```

## 4. XFCE 시작 설정

`/etc/xrdp/startwm.sh` 파일을 열어 아래 내용으로 수정:

```bash
#!/bin/sh
unset DBUS_SESSION_BUS_ADDRESS
unset XDG_RUNTIME_DIR

# dbus로 XFCE 시작
exec dbus-launch --exit-with-session startxfce4
```

권한 확인:

```bash
sudo chmod +x /etc/xrdp/startwm.sh
```

## 5. 방화벽 설정 (UFW 사용 시)

```bash
sudo ufw allow 3389/tcp
sudo ufw reload
```

## 6. 환경 변수 설정 (필요 시, 선택 사항)

`~/.bashrc`에 추가:

```bash
export DISPLAY=:10
```

적용:

```bash
source ~/.bashrc
```

## 7. XRDP 재시작

```bash
sudo systemctl restart xrdp
```

## 8. RDP 클라이언트 연결

* Windows에서 `원격 데스크톱 연결` 또는 `mstsc` 실행
* 서버 IP 입력 후 연결
* 로그인 시 XFCE 세션이 정상적으로 표시되는지 확인

## 9. 확인 및 문제 해결

* 터미널이 뜨지 않거나 창이 안보이면, dbus-x11가 설치되어 있는지 확인
* XFCE 세션에서 로그가 필요하면 `/var/log/xrdp-sesman.log`와 `/var/log/xrdp.log` 확인
