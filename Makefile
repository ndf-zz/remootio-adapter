# SPDX-License-Identifier: MIT
#
# Remootio Adapter - Makefile: avr-gcc, avr-libc & avrdude
#

PROJECT = remootio-adapter
VERSION = 25003

# Build objects
OBJECTS = src/main.o
OBJECTS += src/system.o
OBJECTS += src/console.o
OBJECTS += src/spmcheck.o

# Target binary
TARGET = $(PROJECT).elf

# Listing files
TARGETLIST = $(TARGET:.elf=.lst)

# Random "book" for PRNG seeding
RANDBOOK = randbook.bin

# Compiler
CC = avr-gcc

# Include debugging symbols
DEBUG = -g

# Set language standard
DIALECT = -std=c99 -pedantic

# General code optimisation level
OPTIMISE = -Os
# Don't use jump table for switch statements
#OPTIMISE += -fno-jump-tables
# Mark functions and data so linker can omit dead sections
OPTIMISE += -ffunction-sections -fdata-sections
# Perform link-time optimisation
OPTIMISE += -flto

# Treat all warnings as errors
WARN = -Werror
# Warn on questionable constructs
WARN += -Wall
# Extra warning flags not enabled by -Wall
WARN += -Wextra
# Warn whenever a local variable or type declaration shadows another
WARN += -Wshadow
# Warn if an undefined identifier is evaluated in an #if directive
WARN += -Wundef
# Warn for implicit conversions that may alter a value [annoying]
WARN += -Wconversion

# Avr MCU (Note: 328pb not yet supported in Deb stable avr-libc)
AVROPTS = -mmcu=atmega328p -ffreestanding

# Clock speed
CPPFLAGS = -DF_CPU=2000000L -DSW_VERSION=$(VERSION)

# Add include path for headers
CPPFLAGS += -Iinclude

# Extra libraries
LDLIBS =

# Linker flags - omit unused sections
LDFLAGS = -Wl,--gc-sections

# Combined Compiler flags
CFLAGS = $(DIALECT) $(DEBUG) $(OPTIMISE) $(WARN) $(AVROPTS)
LCFLAGS = CFLAGS

# Binutils
OBJCOPY = avr-objcopy
SIZE = avr-size
NM = avr-nm
NMFLAGS = -n -r
DISFLAGS = -d -S -m avr5
OBJDUMP = avr-objdump

# Python
PYTHON = python3

# Programmer
AVRDUDE = avrdude
PARTNO = m328pb
PROGRAMMER = avrisp2
DUDECMD = $(AVRDUDE) -c $(PROGRAMMER) -p $(PARTNO)
EFUSE = 0xff
LFUSE = 0x7f
HFUSE = 0xc7
LOCKBYTE = 0xff

# Default target
.PHONY: elf
elf: $(TARGET)

# Object dependencies
$(OBJECTS): Makefile include/system.h include/console.h

src/spmcheck.o: include/spm_config.h

src/system.o: include/spmcheck.h

# Build recipes
include/spm_config.h: reference/spm_mkconf.py reference/spm_config.bin reference/spm_config.txt
	$(PYTHON) reference/spm_mkconf.py reference/spm_config.bin reference/spm_config.txt include/spm_config.h

$(TARGET): $(OBJECTS)
	$(CC) $(CFLAGS) $(LDFLAGS) $(LDLIBS) -o $(TARGET) $(OBJECTS)

$(RANDBOOK):
	# Initialise random data
	dd if=/dev/random bs=1K count=1 of=$(RANDBOOK)
	# Zero out configuration space
	dd if=/dev/zero seek=992 bs=1 count=32 of=$(RANDBOOK)

%.o: %.s
	$(CC) $(CPPFLAGS) $(CFLAGS) -c -o $@ $<

%.lst: %.o
	$(OBJDUMP) $(DISFLAGS) $< > $@

%.lst: %.elf
	$(OBJDUMP) $(DISFLAGS) $< > $@

.PHONY: size
size: $(TARGET)
	$(SIZE) $(TARGET)

.PHONY: nm
nm: $(TARGET)
	$(NM) $(NMFLAGS) $(TARGET)

.PHONY: list
list: $(TARGETLIST)

.PHONY: erase
erase:
	$(DUDECMD) -e

.PHONY: upload
upload: $(TARGET)
	$(DUDECMD) -U flash:w:$(TARGET):e

.PHONY: randbook
randbook: $(RANDBOOK)
	$(DUDECMD) -U eeprom:w:$(RANDBOOK):r

# Clear NVR space for FW > v24012
.PHONY: eepatch
eepatch:
	$(DUDECMD) -U eeprom:r:$(RANDBOOK):r
	dd if=/dev/zero seek=1012 bs=1 count=12 of=$(RANDBOOK)
	$(DUDECMD) -U eeprom:w:$(RANDBOOK):r

# Clear console PIN
.PHONY: clrpin
clrpin:
	$(DUDECMD) -U eeprom:r:$(RANDBOOK):r
	dd if=/dev/zero seek=1014 bs=1 count=2 of=$(RANDBOOK)
	$(DUDECMD) -U eeprom:w:$(RANDBOOK):r

.PHONY: fuse
fuse: Makefile
	$(DUDECMD) -U efuse:w:$(EFUSE):m -U hfuse:w:$(HFUSE):m -U lfuse:w:$(LFUSE):m -U lock:w:$(LOCKBYTE):m

.PHONY: clean
clean:
	-rm -f $(TARGET) $(OBJECTS) $(TARGETLIST) $(RANDBOOK)

.PHONY: requires
requires:
	sudo apt-get install gcc-avr binutils-avr avr-libc avrdude

.PHONY: help
help:
	@echo
	@echo Targets:
	@echo " elf [default]   build all objects, link and write $(TARGET)"
	@echo " size            list $(TARGET) section sizes"
	@echo " nm              list all defined symbols in $(TARGET)"
	@echo " list            create text listing for $(TARGET)"
	@echo " erase           bulk erase flash on target"
	@echo " fuse            re-write fuses"
	@echo " upload          write $(TARGET) to flash and verify"
	@echo " clean           remove all intermediate files and logs"
	@echo " requires	install development dependencies"
	@echo
